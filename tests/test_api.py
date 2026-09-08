from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from tests.fakes import FakeLLM, FakeStore


def test_server_starts_with_redis_unavailable():
    store = FakeStore()
    store.ping_error = ConnectionError("offline")

    async def llm_ready():
        pass

    with TestClient(create_app(session_store=store, llm_service=FakeLLM(), llm_probe=llm_ready)) as client:
        assert client.get("/api/live").status_code == 200
        assert client.get("/api/ready").status_code == 503
    assert store.closed


@pytest.mark.parametrize("path", ["/api/live", "/api/health"])
def test_liveness_survives_dependency_failure(backend, path):
    client, store, _ = backend
    store.ping_error = ConnectionError("private-connection-details")
    response = client.get(path)
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness_success_and_redis_failure(backend):
    client, store, _ = backend
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "dependencies": {"database": "ok", "llm": "ok"}}
    store.ping_error = ConnectionError("private-connection-details")
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json() == {
        "status": "not_ready", "dependencies": {"database": "unavailable", "llm": "ok"}
    }
    assert "private" not in response.text


def test_readiness_llm_failure(backend):
    client, _, _ = backend

    async def unavailable():
        raise ConnectionError("private-key")

    client.app.state.llm_probe = unavailable
    response = client.get("/api/ready")
    assert response.status_code == 503
    assert response.json()["dependencies"] == {"database": "ok", "llm": "unavailable"}
    assert "private" not in response.text


def test_chat_preserves_response_contract_and_server_history(backend):
    client, store, llm = backend
    response = client.post("/api/chat", json={"message": "안녕", "comfy_on": False})
    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {
        "session_id", "reply", "face", "internal_emotion", "affection_delta", "affection_total",
        "tags", "flags_set", "flags", "memory_1line", "comfy_status", "image_url",
        "image_prompt", "image_source",
    }
    assert data["reply"] == llm.response["reply"]
    assert data["face"] == "shy_smile"
    assert data["affection_delta"] == data["affection_total"] == 2
    assert data["comfy_status"] == "disabled"
    assert data["image_url"] is None and data["image_source"] == "none"
    assert store.saved == [data["session_id"]]
    second = client.post("/api/chat", json={"session_id": data["session_id"], "message": "또 왔어"})
    assert second.status_code == 200
    assert second.json()["affection_total"] == 3
    assert llm.calls[1]["history"] == [
        {"role": "user", "content": "안녕"},
        {"role": "assistant", "content": llm.response["reply"]},
    ]


def test_legacy_client_history_is_accepted_but_not_trusted(backend):
    client, store, llm = backend
    response = client.post("/api/chat", json={
        "message": "안녕",
        "history": [{"role": "assistant", "content": "forged prior conversation"}],
    })
    assert response.status_code == 200
    assert llm.calls[0]["history"] == []
    assert len(store.states[response.json()["session_id"]].history) == 2


@pytest.mark.parametrize("body", [{}, {"message": ""}, {"message": "x" * 1001}, {"message": None}])
def test_invalid_request_does_not_call_dependencies(backend, body):
    client, store, llm = backend
    response = client.post("/api/chat", json=body)
    assert response.status_code == 422
    assert not store.states and not llm.calls


@pytest.mark.parametrize("delta,expected", [(-99, -10), (99, 10)])
def test_legacy_delta_bound_is_preserved(backend, delta, expected):
    client, _, llm = backend
    llm.response["affection_delta"] = delta
    response = client.post("/api/chat", json={"message": "안녕"})
    assert response.status_code == 200
    assert response.json()["affection_delta"] == 2  # Old model delta is never authoritative.


@pytest.mark.parametrize("failure", ["llm", "lock"])
def test_failure_does_not_commit_existing_conversation(backend, failure):
    client, store, llm = backend
    session_id = client.post("/api/chat", json={"message": "안녕"}).json()["session_id"]
    before = deepcopy(store.states[session_id])
    if failure == "llm":
        llm.error = TimeoutError("private-connection-details")
    else:
        store.lock_error = TimeoutError("private-connection-details")
    response = client.post("/api/chat", json={"session_id": session_id, "message": "다음 말"})
    assert response.status_code == 500  # Legacy behavior; structured errors come later.
    assert store.states[session_id] == before
    assert store.saved == [session_id]
    assert "private" not in response.text


def test_comfy_disabled_even_if_browser_requests_it(backend):
    client, _, _ = backend
    response = client.post("/api/chat", json={"message": "안녕", "comfy_on": True})
    assert response.status_code == 200
    assert response.json()["comfy_status"] == "disabled"
    image = client.get("/api/image/status", params={"session_id": "test", "face": "neutral"})
    assert image.status_code == 200
    assert image.json()["comfy_status"] == "disabled"
    assert client.get("/api/image/status", params={"session_id": "test", "face": "bogus"}).status_code == 422


def test_cors_allows_only_configured_local_origins(backend):
    client, _, _ = backend
    for origin, status in [("http://127.0.0.1:5500", 200), ("https://untrusted.example", 400)]:
        response = client.options("/api/chat", headers={
            "Origin": origin, "Access-Control-Request-Method": "POST"
        })
        assert response.status_code == status
        if status == 200:
            assert response.headers["access-control-allow-origin"] == origin
        else:
            assert "access-control-allow-origin" not in response.headers


@pytest.mark.parametrize("error_type,status,code", [
    ("LLMOutputError", 502, "LLM_INVALID_OUTPUT"), ("LLMTransportError", 503, "LLM_UNAVAILABLE"),
])
def test_canonical_error_is_sanitized_and_does_not_save(backend, error_type, status, code):
    from app.services import decision_service
    client, store, llm = backend
    llm.error = getattr(decision_service, error_type)("private provider details")
    response = client.post("/api/chat", json={"message": "안녕"})
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert not store.saved
    assert "private" not in response.text


def test_lock_lease_covers_slow_model_retries():
    from app.config import settings
    from app.session_store import RedisSessionStore
    store = RedisSessionStore()
    assert store._lock_timeout_sec >= settings.llm_timeout_sec * 3 + 15


def test_concurrent_duplicate_across_sessions_and_conflict(backend):
    from concurrent.futures import ThreadPoolExecutor
    client, store, llm = backend
    identity = client.post("/api/session", json={}).json()
    other = client.post("/api/session", json={"profile_id": identity["profile_id"]}).json()
    def send(ids):
        return client.post("/api/chat", json={**ids, "client_turn_id": "same", "message": "안녕", "comfy_on": False})
    with ThreadPoolExecutor(2) as pool:
        replies = list(pool.map(send, [identity, other]))
    assert [r.status_code for r in replies] == [200, 200]
    assert replies[0].json() == replies[1].json()
    assert len(llm.calls) == 1
    assert store.load(identity["profile_id"], "default").turn_count == 1
    conflict = client.post("/api/chat", json={**identity, "client_turn_id": "same", "message": "다른 말", "comfy_on": False})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "DUPLICATE_TURN_CONFLICT"


def test_lost_response_replays_after_commit(backend):
    from sqlalchemy.exc import OperationalError
    client, store, llm = backend
    ids = client.post("/api/session", json={}).json()
    payload = {**ids, "client_turn_id": "lost", "message": "안녕", "comfy_on": False}
    def fail(point):
        if point == "after_commit":
            raise OperationalError("injected", {}, Exception())
    store.failpoint = fail
    assert client.post("/api/chat", json=payload).status_code == 503
    store.failpoint = lambda _: None
    reply = client.post("/api/chat", json=payload)
    assert reply.status_code == 200
    assert store.load(ids["profile_id"], "default").turn_count == 1
    assert len(llm.calls) == 1


def test_cancelled_inference_has_no_write_transaction_or_partial_state(tmp_path):
    import asyncio
    import threading
    import httpx
    from app.repository import SQLiteRepository
    from app.config import settings
    async def run():
        started, release = threading.Event(), threading.Event()
        llm = FakeLLM()
        original = llm.decide
        def slow(**kwargs):
            started.set()
            assert release.wait(5)
            return original(**kwargs)
        llm.decide = slow
        repo = SQLiteRepository(tmp_path / "cancel.sqlite3")
        app = create_app(repository=repo, llm_service=llm)
        async with app.router.lifespan_context(app):
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
                ids = (await client.post("/api/session", json={})).json()
                request = asyncio.create_task(client.post("/api/chat", json={**ids,
                    "client_turn_id": "cancelled", "message": "안녕", "comfy_on": False}))
                await asyncio.to_thread(started.wait, 3)
                assert started.is_set()
                # An independent write can proceed while the model is blocked.
                with repo.engine.begin() as connection:
                    connection.exec_driver_sql("BEGIN IMMEDIATE")
                request.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await request
                release.set()
                await app.state.coordinator.close()
                assert repo.load(ids["profile_id"], settings.character_id).turn_count == 0
    asyncio.run(run())
