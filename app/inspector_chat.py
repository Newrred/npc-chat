"""Narrow loopback bridge to the real guest API; all state mutations stay in the web app."""
import asyncio
from http.cookies import SimpleCookie
import json
from urllib.parse import urlsplit

import httpx
from fastapi import Request
from fastapi.responses import JSONResponse

from app.guest_access import COOKIE, LIFETIME

LOCAL_COOKIE = "npc_inspector_guest"
WRITES = {"/api/test/session", "/api/test/chat", "/api/test/reset"}
ROUTES = {"session": "/api/session", "chat": "/api/chat", "reset": "/api/conversation/reset",
          "conversation": "/api/conversation"}


def mount_chat(app, origin, transport=None, database=None):
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path or parsed.query or parsed.fragment or parsed.username:
        raise ValueError("Inspector chat requires an exact guest HTTPS origin")

    @app.api_route("/api/test/{operation}", methods=["GET", "POST"])
    async def bridge(operation: str, request: Request):
        if operation not in ROUTES or request.method != ("GET" if operation == "conversation" else "POST"):
            return JSONResponse({"error": "지원하지 않는 테스트 요청입니다."}, status_code=404)
        body = None
        draft = None
        if request.method == "POST":
            raw = bytearray()
            try:
                async with asyncio.timeout(10):
                    async for chunk in request.stream():
                        raw.extend(chunk)
                        if len(raw) > 16384:
                            return JSONResponse({"error": "요청이 너무 큽니다."}, status_code=413)
                body = json.loads(raw)
                if not isinstance(body, dict):
                    raise ValueError()
            except (ValueError, TimeoutError):
                return JSONResponse({"error": "JSON 요청을 확인해 주세요."}, status_code=400)
            if operation == "chat" and body.get("prompt_draft") is not None:
                from app.inspector_prompt import PromptDraft
                try:
                    draft = PromptDraft.model_validate(body["prompt_draft"])
                except ValueError:
                    return JSONResponse({"error": "캐릭터 소개 1~1500자, 말투·규칙 1~3500자를 입력해 주세요."}, status_code=422)
            allowed = {"session_id", "profile_id", "client_turn_id", "message"} if operation == "chat" else {"session_id", "profile_id"}
            body = {} if operation == "session" else {k: v for k, v in body.items() if k in allowed}
        headers = {"Host": parsed.netloc, "Origin": origin}
        if draft is not None:
            from app.inspector_prompt import issue
            headers["X-NPC-Local-Prompt"] = issue(database, draft, body)
        cookie = request.cookies.get(LOCAL_COOKIE, "")
        if cookie and len(cookie) <= 512 and all(c.isalnum() or c == "." for c in cookie):
            headers["Cookie"] = f"{COOKIE}={cookie}"
        params = {k: v for k, v in request.query_params.items() if k in {"session_id", "profile_id", "before", "limit"}}
        try:
            async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", trust_env=False,
                                         timeout=390, transport=transport, follow_redirects=False) as client:
                response = await client.request(request.method, ROUTES[operation], headers=headers, json=body, params=params)
                result = JSONResponse(response.json(), status_code=response.status_code)
                cookies = SimpleCookie()
                for header in response.headers.get_list("set-cookie"):
                    cookies.load(header)
                if COOKIE in cookies:
                    result.set_cookie(LOCAL_COOKIE, cookies[COOKIE].value, httponly=True,
                                      samesite="strict", max_age=LIFETIME, path="/api/test")
                return result
        except (httpx.HTTPError, ValueError):
            return JSONResponse({"error": "웹 서버의 응답을 확인하지 못했습니다. 같은 메시지로 재시도할 수 있습니다."}, status_code=503)
