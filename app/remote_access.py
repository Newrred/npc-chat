"""Opt-in remote boundary; local inference never depends on an identity provider."""
import asyncio
from collections import deque
from dataclasses import dataclass
import hashlib
import logging
import os
import re
import time
import uuid
from urllib.parse import urlsplit

from fastapi.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.errors import ChatError
from app.guest_access import GuestIdentity


@dataclass(frozen=True)
class RemoteConfig:
    mode: str = "local"
    origin: str = ""
    issuer: str = ""
    audience: str = ""
    requests_per_minute: int = 20
    max_users: int = 1000
    body_bytes: int = 16384
    guest_secret: str = ""
    active_visitors: int = 5
    visitor_ttl: int = 300
    daily_total: int = 200
    daily_visitor: int = 30

    @classmethod
    def from_env(cls):
        return cls(mode=os.getenv("NPC_ACCESS_MODE", "local"),
                   origin=os.getenv("NPC_PUBLIC_ORIGIN", ""),
                   issuer=os.getenv("NPC_ACCESS_ISSUER", ""),
                   audience=os.getenv("NPC_ACCESS_AUDIENCE", ""),
                   requests_per_minute=int(os.getenv("NPC_REQUESTS_PER_MINUTE", "20")),
                   guest_secret=os.getenv("NPC_GUEST_SECRET", ""),
                   active_visitors=int(os.getenv("NPC_ACTIVE_VISITORS", "5")),
                   visitor_ttl=int(os.getenv("NPC_VISITOR_TTL", "300")),
                   daily_total=int(os.getenv("NPC_DAILY_TOTAL", "200")),
                   daily_visitor=int(os.getenv("NPC_DAILY_VISITOR", "30")))

    def validate(self):
        if self.mode not in {"local", "cloudflare", "guest"}:
            raise ValueError("NPC_ACCESS_MODE must be local, cloudflare or guest")
        if self.mode == "local":
            return
        url = urlsplit(self.origin)
        if (url.scheme != "https" or not url.hostname or url.username or url.password
                or url.path or url.query or url.fragment):
            raise ValueError("NPC_PUBLIC_ORIGIN must be an exact HTTPS origin without trailing slash")
        if not 1 <= self.requests_per_minute <= 120:
            raise ValueError("Request limit must be between 1 and 120")
        if self.mode == "guest":
            if len(self.guest_secret) < 64 or len(set(self.guest_secret)) < 8:
                raise ValueError("NPC_GUEST_SECRET requires a persistent randomly generated secret of at least 64 characters")
            if not (1 <= self.active_visitors <= 100 and 30 <= self.visitor_ttl <= 3600
                    and 1 <= self.daily_visitor <= self.daily_total <= 100000):
                raise ValueError("Invalid guest usage limits")
            return
        if not re.fullmatch(r"https://[a-z0-9-]+\.cloudflareaccess\.com", self.issuer):
            raise ValueError("NPC_ACCESS_ISSUER must be the HTTPS Cloudflare team origin")
        if not self.audience or not 1 <= self.requests_per_minute <= 120:
            raise ValueError("Access audience and a request limit between 1 and 120 are required")


class AccessVerifier:
    def __init__(self, config):
        import jwt
        self.jwt = jwt
        self.config = config
        self.jwks = jwt.PyJWKClient(config.issuer + "/cdn-cgi/access/certs", timeout=3)

    def __call__(self, token):
        try:
            key = self.jwks.get_signing_key_from_jwt(token).key
            claims = self.jwt.decode(token, key, algorithms=["RS256"], issuer=self.config.issuer,
                                     audience=self.config.audience,
                                     options={"require": ["exp", "iat", "iss", "aud", "sub"]})
            if not isinstance(claims["sub"], str) or not claims["sub"]:
                raise ValueError("Missing identity")
            # No email or provider identity is persisted in the conversation database.
            return hashlib.sha256((self.config.issuer + "\0" + claims["sub"]).encode()).hexdigest()
        except self.jwt.PyJWKClientConnectionError:
            raise ChatError("AUTH_UNAVAILABLE", "로그인 확인 서버에 연결할 수 없습니다.", 503, True) from None
        except (self.jwt.PyJWTError, ValueError, KeyError):
            raise ChatError("AUTH_REQUIRED", "로그인이 필요합니다. 페이지를 새로고침해 주세요.", 401) from None


class RemoteBoundary:
    def __init__(self, app, *, config, verifier):
        self.app, self.config, self.verifier = app, config, verifier
        self.windows = {}
        self.active = set()
        self.auth_slots = asyncio.Semaphore(4)
        self.guest = GuestIdentity(config.guest_secret) if config.mode == "guest" else None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request_id = uuid.uuid4().hex
        started = time.monotonic()
        headers = {key.decode("latin-1").lower(): value.decode("latin-1") for key, value in scope["headers"]}
        owner = None
        acquired = False
        status = 500
        guest_cookie = None

        async def response_send(message):
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                message["headers"] = list(message["headers"]) + [
                    (b"x-request-id", request_id.encode()), (b"cache-control", b"no-store"),
                    (b"x-content-type-options", b"nosniff"), (b"x-frame-options", b"DENY"),
                    (b"referrer-policy", b"no-referrer")]
                if guest_cookie:
                    message["headers"].append((b"set-cookie", guest_cookie.encode()))
            await send(message)

        try:
            # Only anonymous liveness is exempt; readiness and assets also require authentication.
            if scope["path"] not in {"/api/live", "/api/health"}:
                if headers.get("host") != urlsplit(self.config.origin).netloc:
                    raise ChatError("HOST_REJECTED", "허용되지 않은 주소입니다.", 403)
                if self.guest:
                    if scope["path"] == "/api/ready":
                        raise ChatError("ACCESS_DENIED", "공개되지 않은 경로입니다.", 403)
                    owner, guest_cookie = self.guest.identify(headers.get("cookie", ""))
                else:
                    token = headers.get("cf-access-jwt-assertion", "")
                    if not token or len(token) > 16384:
                        raise ChatError("AUTH_REQUIRED", "로그인이 필요합니다. 페이지를 새로고침해 주세요.", 401)
                    if self.auth_slots.locked():
                        raise ChatError("AUTH_BUSY", "로그인 확인이 혼잡합니다.", 503, True)
                    async with self.auth_slots:
                        owner = await run_in_threadpool(self.verifier, token)
                scope.setdefault("state", {})["remote_owner"] = owner
                # Cookie-authenticated browser writes require the exact origin, even if Origin is omitted.
                if scope["method"] not in {"GET", "HEAD", "OPTIONS"}:
                    if headers.get("origin") != self.config.origin:
                        raise ChatError("ORIGIN_REJECTED", "허용되지 않은 요청 출처입니다.", 403)
                    if headers.get("content-type", "").split(";")[0] != "application/json":
                        raise ChatError("JSON_REQUIRED", "JSON 요청이 필요합니다.", 415)
                    now = time.monotonic()
                    self.windows = {key: values for key, values in self.windows.items()
                                    if values and values[-1] > now - 60}
                    if owner not in self.windows and len(self.windows) >= self.config.max_users:
                        raise ChatError("SERVER_BUSY", "접속자가 많습니다.", 503, True)
                    window = self.windows.setdefault(owner, deque())
                    while window and window[0] <= now - 60:
                        window.popleft()
                    if len(window) >= self.config.requests_per_minute:
                        raise ChatError("RATE_LIMITED", "요청이 많습니다. 잠시 후 다시 시도해 주세요.", 429, True)
                    window.append(now)
                    if scope["path"] in {"/api/chat", "/api/conversation/reset"}:
                        if owner in self.active:
                            raise ChatError("TURN_IN_PROGRESS", "이전 대화가 처리 중입니다.", 429, True)
                        self.active.add(owner)
                        acquired = True
                # Count streamed bytes too; Content-Length alone is not a size boundary.
                body = bytearray()
                while True:
                    try:
                        message = await asyncio.wait_for(receive(), timeout=10)
                    except TimeoutError:
                        raise ChatError("REQUEST_TIMEOUT", "요청 전송 시간이 초과됐습니다.", 408, True) from None
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > self.config.body_bytes:
                        raise ChatError("BODY_TOO_LARGE", "입력이 너무 큽니다.", 413)
                    if not message.get("more_body", False):
                        break
                delivered = False

                async def replay_receive():
                    nonlocal delivered
                    if delivered:
                        return await receive()
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}

                await self.app(scope, replay_receive, response_send)
            else:
                await self.app(scope, receive, response_send)
        except ChatError as exc:
            response = JSONResponse({"error": {"code": exc.code, "message": exc.message,
                                              "retryable": exc.retryable}, "request_id": request_id},
                                    status_code=exc.status,
                                    headers={"Retry-After": "60"} if exc.status == 429 else None)
            await response(scope, receive, response_send)
        finally:
            if acquired:
                self.active.discard(owner)
            # Deliberately omit query strings, tokens, identities and conversation text.
            logging.getLogger(__name__).info("request_complete id=%s status=%s duration_ms=%d",
                                             request_id, status, (time.monotonic() - started) * 1000)
