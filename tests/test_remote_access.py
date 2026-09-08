from dataclasses import replace
import asyncio
import time
from types import SimpleNamespace

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import httpx
import pytest

from app.errors import ChatError
from app.main import create_app
from app.remote_access import AccessVerifier, RemoteBoundary, RemoteConfig
from app.repository import SQLiteRepository
from tests.fakes import FakeLLM
from app.relationship import RelationshipState
from scripts.remote_preflight import inspect


CONFIG = RemoteConfig(mode="cloudflare", origin="https://chat.example.com",
                      issuer="https://example.cloudflareaccess.com", audience="test-audience")


@pytest.fixture
def remote(tmp_path):
    repo = SQLiteRepository(tmp_path / "remote.sqlite3")
    def verify(token):
        if token not in {"alice", "bob"}:
            raise ChatError("AUTH_REQUIRED", "로그인 필요", 401)
        return token
    app = create_app(repository=repo, llm_service=FakeLLM(), remote_config=CONFIG, access_verifier=verify)
    with TestClient(app, base_url=CONFIG.origin) as client:
        yield client, repo


def headers(user="alice"):
    return {"Cf-Access-Jwt-Assertion": user, "Origin": CONFIG.origin}


@pytest.mark.parametrize("path", ["/", "/app.js", "/config.js", "/api/ready", "/docs", "/api/image/status"])
def test_remote_requires_authentication_for_page_assets_and_api(remote, path):
    client, _ = remote
    response = client.get(path)
    assert response.status_code == 401
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-request-id"]
    assert client.get("/api/live").status_code == 200


def test_remote_page_and_account_isolation(remote):
    client, repo = remote
    assert client.get("/", headers=headers()).status_code == 200
    assert client.get("/docs", headers=headers()).status_code == 404
    alice = client.post("/api/session", json={}, headers=headers()).json()
    bob = client.post("/api/session", json={}, headers=headers("bob")).json()
    assert alice["profile_id"] != bob["profile_id"]
    assert client.post("/api/session", json={}, headers=headers()).json() == alice
    for route, body in [("/api/session", alice), ("/api/chat", {**alice, "message": "안녕", "client_turn_id": "x"})]:
        assert client.post(route, json=body, headers=headers("bob")).status_code == 403
    assert client.get("/api/image/status", params={"session_id": alice["session_id"], "face": "happy"},
                      headers=headers("bob")).status_code == 403
    request = {**alice, "message": "안녕", "client_turn_id": "one"}
    first = client.post("/api/chat", json=request, headers=headers())
    assert first.status_code == 200
    assert client.post("/api/chat", json=request, headers=headers()).json() == first.json()
    assert repo.load(alice["profile_id"], "default").turn_count == 1
    assert repo.load(bob["profile_id"], "default").turn_count == 0


@pytest.mark.parametrize("origin", [None, "https://evil.example", "null"])
def test_remote_csrf_rejected(remote, origin):
    client, _ = remote
    request_headers = headers()
    request_headers.pop("Origin")
    if origin:
        request_headers["Origin"] = origin
    assert client.post("/api/session", json={}, headers=request_headers).status_code == 403


def test_remote_host_body_and_rate_limits(remote):
    client, _ = remote
    assert client.get("/", headers={**headers(), "Host": "evil.example"}).status_code == 403
    assert client.post("/api/session", content="x" * 16385,
                       headers={**headers(), "Content-Type": "application/json"}).status_code == 413
    for _ in range(19):
        assert client.post("/api/session", json={}, headers=headers()).status_code == 200
    response = client.post("/api/session", json={}, headers=headers())
    assert response.status_code == 429 and response.headers["Retry-After"] == "60"
    assert client.post("/api/session", json={}, headers=headers("bob")).status_code == 200


@pytest.mark.parametrize("updates", [{"mode": "unknown"}, {"origin": "http://chat.example.com"},
    {"origin": "https://chat.example.com/"}, {"issuer": "https://evil.example"}, {"audience": ""},
    {"requests_per_minute": 0}])
def test_invalid_remote_configuration_fails_closed(updates):
    with pytest.raises(ValueError):
        replace(CONFIG, **updates).validate()


@pytest.fixture
def signed():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    verifier = AccessVerifier(CONFIG)
    verifier.jwks = SimpleNamespace(get_signing_key_from_jwt=lambda token: SimpleNamespace(key=key.public_key()))
    claims = {"iss": CONFIG.issuer, "aud": CONFIG.audience, "sub": "alice", "iat": int(time.time()),
              "exp": int(time.time()) + 300}
    return key, verifier, claims


def test_signed_identity_is_stable_and_not_email(signed):
    key, verifier, claims = signed
    token = jwt.encode(claims, key, algorithm="RS256")
    assert len(verifier(token)) == 64
    assert verifier(token) == verifier(jwt.encode({**claims, "email": "changed@example.com"}, key, algorithm="RS256"))


@pytest.mark.parametrize("updates", [{"aud": "wrong"}, {"iss": "https://evil.example"}, {"exp": 1},
                                   {"iat": 9999999999}, {"sub": ""}])
def test_invalid_signed_claims_are_rejected(signed, updates):
    key, verifier, claims = signed
    with pytest.raises(ChatError) as exc:
        verifier(jwt.encode({**claims, **updates}, key, algorithm="RS256"))
    assert exc.value.status == 401


def test_unsigned_wrong_signature_and_missing_exp_rejected(signed):
    key, verifier, claims = signed
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    tokens = [jwt.encode(claims, other, algorithm="RS256"), jwt.encode(claims, key="", algorithm="none"),
              jwt.encode({k: v for k, v in claims.items() if k != "exp"}, key, algorithm="RS256")]
    for token in tokens:
        with pytest.raises(ChatError):
            verifier(token)


def test_key_service_outage_fails_closed(signed):
    _, verifier, _ = signed
    def unavailable(token):
        raise jwt.PyJWKClientConnectionError("private URL")
    verifier.jwks.get_signing_key_from_jwt = unavailable
    with pytest.raises(ChatError) as exc:
        verifier("token")
    assert exc.value.status == 503 and "private" not in exc.value.message


def test_remote_ownership_survives_restart_and_rejects_legacy(tmp_path):
    path = tmp_path / "state.sqlite3"
    repo = SQLiteRepository(path)
    repo.upgrade()
    legacy = repo.resolve(None, None, "default", RelationshipState())
    remote = repo.resolve_owned("alice", None, None, "default", RelationshipState(), create=True)
    repo.engine.dispose()
    repo = SQLiteRepository(path)
    try:
        repo.upgrade()
        assert repo.resolve_owned("alice", *remote, "default", RelationshipState()) == remote
        with pytest.raises(ChatError):
            repo.resolve_owned("alice", *legacy, "default", RelationshipState(), create=True)
        assert repo.resolve(*legacy, "default", RelationshipState()) == legacy
    finally:
        repo.engine.dispose()


def test_concurrent_user_limit_and_release():
    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()
        async def app(scope, receive, send):
            if scope["state"]["remote_owner"] == "alice":
                entered.set()
                await release.wait()
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"{}"})
        boundary = RemoteBoundary(app, config=CONFIG, verifier=lambda token: token)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=boundary), base_url=CONFIG.origin) as client:
            first = asyncio.create_task(client.post("/api/chat", json={}, headers=headers()))
            await asyncio.wait_for(entered.wait(), 2)
            second = await client.post("/api/chat", json={}, headers=headers())
            assert second.status_code == 429
            assert (await client.post("/api/chat", json={}, headers=headers("bob"))).status_code == 200
            release.set()
            assert (await first).status_code == 200
            assert (await client.post("/api/chat", json={}, headers=headers())).status_code == 200
            assert not boundary.active
    asyncio.run(scenario())


def test_chunked_body_limit(remote):
    client, _ = remote
    response = client.post("/api/session", content=iter([b"x" * 8192] * 3),
                           headers={**headers(), "Content-Type": "application/json"})
    assert response.status_code == 413


def test_preflight_template_is_not_deployable():
    result = inspect({})
    assert not result["configuration_ready"] and not result["release_ready"]
    assert len(result["errors"]) >= 6


def test_preflight_valid_config_does_not_claim_release_ready(tmp_path):
    model, binary = tmp_path / "model.gguf", tmp_path / "llama-server.exe"
    model.touch()
    binary.touch()
    values = {"NPC_ACCESS_MODE": "cloudflare", "NPC_PUBLIC_ORIGIN": CONFIG.origin,
              "NPC_ACCESS_ISSUER": CONFIG.issuer, "NPC_ACCESS_AUDIENCE": CONFIG.audience,
              "NPC_DATABASE_PATH": str(tmp_path / "persistent" / "remote.sqlite3"),
              "NPC_BASE_URL": "http://127.0.0.1:8001/v1", "LLAMA_MODEL_PATH": str(model),
              "LLAMA_SERVER_PATH": str(binary), "NPC_MODEL": "model", "NPC_TOKEN_COUNT_MODE": "llama_cpp",
              "COMFY_ENABLED": "false", "COMFY_CONNECT": "false"}
    result = inspect(values)
    assert result["configuration_ready"] and not result["release_ready"]
