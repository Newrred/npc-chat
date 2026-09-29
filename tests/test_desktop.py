import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from scripts.desktop_runtime import wait
from scripts.desktop_server import create_desktop_app


@pytest.fixture
def desktop(monkeypatch):
    monkeypatch.setenv("NPC_DESKTOP_TOKEN", "x" * 64)
    app = FastAPI()

    @app.get("/api/live")
    def live():
        return {"status": "ok"}

    monkeypatch.setattr("app.main.create_app", lambda: app)
    with TestClient(create_desktop_app(), base_url="http://127.0.0.1:8003") as client:
        yield client


@pytest.mark.parametrize("headers", [
    {}, {"X-NPC-Desktop": "wrong"},
    {"X-NPC-Desktop": "x" * 64, "Origin": "https://example.com"},
    {"X-NPC-Desktop": "x" * 64, "Origin": "null"},
    {"X-NPC-Desktop": "x" * 64, "Host": "evil.example:8003"},
])
def test_desktop_rejects_foreign_requests(desktop, headers):
    assert desktop.get("/api/live", headers=headers).status_code == 403


@pytest.mark.parametrize("headers", [
    {"X-NPC-Desktop": "x" * 64, "Origin": "http://127.0.0.1:8003"},
    {"Authorization": "Bearer " + "x" * 64},
])
def test_desktop_accepts_own_client_and_health(desktop, headers):
    response = desktop.get("/api/live", headers=headers)
    assert response.status_code == 200
    assert "script-src 'self'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_desktop_refuses_missing_token(monkeypatch):
    monkeypatch.delenv("NPC_DESKTOP_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="token"):
        create_desktop_app()


def test_supervisor_readiness_cancellation_and_exit(monkeypatch):
    from scripts import desktop_runtime
    stopped = threading.Event()
    stopped.set()
    with pytest.raises(RuntimeError, match="START_CANCELLED"):
        wait({}, "unused", "token", stopped)
    stopped.clear()
    monkeypatch.setattr(desktop_runtime, "matches", lambda _: False)
    with pytest.raises(RuntimeError, match="PROCESS_EXITED"):
        wait({}, "unused", "token", stopped)
    monkeypatch.setattr(desktop_runtime, "matches", lambda _: True)
    monkeypatch.setattr(desktop_runtime, "ready", lambda *args: True)
    wait({}, "unused", "token", stopped)
