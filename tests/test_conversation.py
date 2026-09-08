from dataclasses import replace
import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.admin import create_admin
from app.main import create_app, settings
from app.repository import SQLiteRepository
from app.storage_schema import turns, memories, sessions
from tests.fakes import FakeLLM
from tests.test_guest_access import CONFIG, HEADERS


def local_client(tmp_path):
    repo = SQLiteRepository(tmp_path / "chat.sqlite3")
    return repo, TestClient(create_app(repository=repo, llm_service=FakeLLM()))


def send(client, identity, turn="a", headers=None):
    result = client.post("/api/chat", json={**identity, "client_turn_id": turn,
                                           "message": "합성 테스트 " + turn}, headers=headers)
    assert result.status_code == 200, result.text
    return result.json()


def test_history_pages_ties_and_restart(tmp_path):
    repo, client = local_client(tmp_path)
    with client:
        identity = client.post("/api/session", json={}).json()
        for turn in ["a", "b", "c"]:
            send(client, identity, turn)
        with repo.engine.begin() as db:
            db.execute(update(turns).values(created=100))
        first = client.get("/api/conversation", params={**identity, "limit": 2})
        assert first.headers["cache-control"] == "no-store"
        assert [t["turn_id"] for t in first.json()["items"]] == ["b", "c"]
        second = client.get("/api/conversation", params={**identity, "before": first.json()["before"]})
        assert [t["turn_id"] for t in second.json()["items"]] == ["a"]
        assert set(second.json()["items"][0]) == {"turn_id", "reply", "user_message", "face", "created"}
        assert client.get("/api/conversation", params={**identity, "limit": 1000}).status_code == 422
        assert client.get("/api/conversation", params={**identity, "before": "absent"}).status_code == 409
    _, restarted = local_client(tmp_path)
    with restarted:
        assert len(restarted.get("/api/conversation", params=identity).json()["items"]) == 3


def test_reset_revokes_old_session_preserves_other_room_and_rejects_retry(tmp_path):
    repo, client = local_client(tmp_path)
    with client:
        identity = client.post("/api/session", json={}).json()
        other = client.post("/api/session", json={}).json()
        send(client, identity)
        send(client, other)
        before = repo.load(identity["profile_id"], settings.character_id)
        assert client.post("/api/conversation/reset", json=identity).json() == {"closed": True}
        state = repo.load(identity["profile_id"], settings.character_id)
        assert state.values == client.app.state.character.initial_relationship
        assert state.version > before.version
        assert not state.history and not state.flags and not state.summary and not state.turn_count
        with repo.engine.connect() as db:
            for table in [turns, memories, sessions]:
                assert not db.execute(select(table).where(table.c.profile_id == identity["profile_id"])).all()
        new = client.post("/api/session", json={"profile_id": identity["profile_id"]}).json()
        send(client, new, "new")
        assert client.post("/api/conversation/reset", json=identity).status_code == 404
        assert client.post("/api/chat", json={**identity, "client_turn_id": "stale", "message": "stale"}).status_code == 404
        assert len(client.get("/api/conversation", params=new).json()["items"]) == 1
        assert len(client.get("/api/conversation", params=other).json()["items"]) == 1


def test_reset_rolls_back_atomically(tmp_path):
    repo, client = local_client(tmp_path)
    with client:
        identity = client.post("/api/session", json={}).json()
        send(client, identity)
        def fail(name):
            if name == "after_reset":
                raise sqlite3.OperationalError("synthetic failure")
        repo.failpoint = fail
        assert client.post("/api/conversation/reset", json=identity).status_code == 503
        assert len(client.get("/api/conversation", params=identity).json()["items"]) == 1
        assert repo.load(identity["profile_id"], settings.character_id).turn_count == 1


def test_guest_read_reset_ownership_origin_and_quota(tmp_path):
    config = replace(CONFIG, daily_visitor=1, daily_total=2)
    repo = SQLiteRepository(tmp_path / "guest.sqlite3")
    with TestClient(create_app(repository=repo, llm_service=FakeLLM(), remote_config=config),
                    base_url=config.origin) as client:
        identity = client.post("/api/session", json={}, headers=HEADERS).json()
        send(client, identity, headers=HEADERS)
        cookies = dict(client.cookies)
        client.cookies.clear()
        assert client.get("/api/conversation", params=identity).status_code == 403
        assert client.post("/api/conversation/reset", json=identity, headers=HEADERS).status_code == 403
        client.cookies.clear()
        client.cookies.update(cookies)
        assert client.get("/api/conversation", params=identity).status_code == 200
        assert client.post("/api/conversation/reset", json=identity).status_code == 403
        assert client.post("/api/conversation/reset", json=identity, headers=HEADERS).status_code == 200
        new = client.post("/api/session", json={}, headers=HEADERS).json()
        assert new["profile_id"] == identity["profile_id"]
        assert new["session_id"] != identity["session_id"]
        limited = client.post("/api/chat", json={**new, "message": "다시", "client_turn_id": "b"}, headers=HEADERS)
        assert limited.json()["error"]["code"] == "DAILY_VISITOR_LIMIT"
        for path in ["/admin", "/admin/index.html", "/api/rooms", "/api/turns"]:
            assert client.get(path).status_code == 404


def test_queued_chat_revalidates_session_before_inference(tmp_path):
    repo, client = local_client(tmp_path)
    with client:
        identity = client.post("/api/session", json={}).json()
        async def intercepted(execute):
            repo.reset_conversation(**identity, character_id=settings.character_id,
                                    defaults=client.app.state.character.initial_relationship)
            return await execute(lambda: False)
        client.app.state.coordinator.submit = intercepted
        response = client.post("/api/chat", json={**identity, "message": "대기 중", "client_turn_id": "old"})
        assert response.status_code == 404
        assert not client.app.state.llm_service.calls


@pytest.mark.parametrize("headers", [{"Host": "evil.example"}, {"Origin": "https://evil.example"},
                                    {"Sec-Fetch-Site": "cross-site"}])
def test_admin_rejects_browser_cross_origin(tmp_path, headers):
    with TestClient(create_admin(tmp_path / "absent"), base_url="http://127.0.0.1:8002",
                    client=("127.0.0.1", 1234)) as client:
        assert client.get("/api/rooms", headers=headers).status_code == 403


def test_admin_local_read_only_listing_and_private_database_failure(tmp_path):
    repo, client = local_client(tmp_path)
    with client:
        identity = client.post("/api/session", json={}).json()
        send(client, identity)
        with TestClient(create_admin(repo.path), base_url="http://127.0.0.1:8002",
                        client=("127.0.0.1", 1234)) as admin:
            assert admin.get("/").status_code == 200
            assert admin.get("/api/ready").status_code == 200
            rooms = admin.get("/api/rooms")
            assert rooms.headers["cache-control"] == "no-store"
            room = rooms.json()["items"][0]
            assert room["profile_id"] == identity["profile_id"] and room["turns"] == 1
            assert len(admin.get("/api/turns", params={"profile_id": room["profile_id"],
                           "character_id": room["character_id"]}).json()["items"]) == 1
            assert admin.post("/api/conversation/reset", json=identity).status_code == 403
        assert repo.load(identity["profile_id"], settings.character_id).turn_count == 1
    absent = tmp_path / "absent.sqlite3"
    with TestClient(create_admin(absent), base_url="http://127.0.0.1:8002",
                    client=("127.0.0.1", 1234)) as admin:
        response = admin.get("/api/ready")
        assert response.status_code == 503 and str(absent) not in response.text
    assert not absent.exists()
    with TestClient(create_admin(repo.path), base_url="http://127.0.0.1:8002",
                    client=("192.168.0.2", 1234)) as admin:
        assert admin.get("/").status_code == 403
