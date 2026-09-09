import json
import sqlite3
import time

from fastapi.testclient import TestClient

from app.admin import create_admin
from app.debug_trace import capture, emit, read, trace_path, forget
from tests.test_decision import service, valid


def test_disabled_capture_never_creates_private_file(tmp_path):
    path = tmp_path / "db"
    with capture(path, False, "p", "c", "t"):
        emit("request", messages=["private"])
    assert not trace_path(path).exists()


def test_exact_requests_outputs_failures_and_no_credentials(tmp_path):
    path = tmp_path / "db"
    adapter, calls = service(["bad", valid()])
    with capture(path, True, "p", "c", "t"):
        adapter.decide(message="synthetic question")
    events = read(path)[0]["events"]
    requests = [e for e in events if e["event"] == "request"]
    expanded = [{k: v for k, v in e["request"].items() if k != "extra_body"} |
                e["request"]["extra_body"] for e in requests]
    assert expanded == calls
    assert len([e for e in events if e["event"] == "output"]) == 2
    assert any(e["event"] == "validation_failure" for e in events)
    assert "api_key" not in json.dumps(events) and "Authorization" not in json.dumps(events)
    adapter.client.close()


def test_retention_exception_and_forget(tmp_path):
    path = tmp_path / "db"
    for i in range(103):
        with capture(path, True, "p", "c", str(i)):
            emit("request")
    assert len(read(path)) == 100
    try:
        with capture(path, True, "other", "c", "failed"):
            raise ValueError("private error detail")
    except ValueError:
        pass
    assert read(path)[0]["events"][-1]["error_type"] == "ValueError"
    assert "private error detail" not in str(read(path))
    forget(path, "p", "c")
    assert len(read(path)) == 1
    with sqlite3.connect(trace_path(path)) as db:
        db.execute("UPDATE traces SET updated=?", (time.time()-3601,))
    assert read(path) == []


def test_api_trace_admin_only_and_reset(backend, monkeypatch):
    from app.main import settings
    client, store, _ = backend
    monkeypatch.setattr(settings, "debug_trace", True)
    ids = client.post("/api/session", json={}).json()
    payload = {**ids, "client_turn_id": "inspect", "message": "내 이름은 민석이야"}
    assert client.post("/api/chat", json=payload).status_code == 200
    traces = read(store.path)
    assert traces[0]["events"][-1]["event"] == "completed"
    with TestClient(create_admin(store.path), base_url="http://127.0.0.1:8002", client=("127.0.0.1", 1)) as admin:
        assert admin.get("/inspector").status_code == 200
        data = admin.get("/api/inspector", params={"profile_id": ids["profile_id"]}).json()
        assert len(data["detail"]) == 1
        assert "민석" in str(data["current_memory"]["derived_profile"])
        assert admin.get("/api/inspector", headers={"Origin": "https://evil.example"}).status_code == 403
        assert admin.post("/api/inspector").status_code == 403
        assert client.get("/api/inspector").status_code == 404
        assert client.post("/api/conversation/reset", json=ids).status_code == 200
        assert admin.get("/api/inspector").json()["traces"] == []
    assert read(store.path) == []


def test_stored_memory_mapping_and_diagnostic_outage_do_not_break_chat(backend, monkeypatch):
    from app.main import settings
    import app.debug_trace as trace
    from tests.test_memory_api import seed
    client, store, _ = backend
    monkeypatch.setattr(settings, "debug_trace", True)
    ids = client.post("/api/session", json={}).json()
    seed(store, ids["profile_id"], "나는 커피를 좋아해.", kind="preference")
    payload = {**ids, "message": "커피", "client_turn_id": "mapping"}
    assert client.post("/api/chat", json=payload).status_code == 200
    events = read(store.path)[0]["events"]
    assert next(e for e in events if e["event"] == "context_selected")["selected_memories"][0]["kind"] == "preference"
    def broken(*args):
        raise sqlite3.OperationalError("synthetic")
    monkeypatch.setattr(trace, "connection", broken)
    assert client.post("/api/chat", json={**payload, "client_turn_id": "outage"}).status_code == 200
