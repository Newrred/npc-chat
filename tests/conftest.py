import os
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

# Tests must never read the user's .env or use a configured remote endpoint.
for key in list(os.environ):
    if key.startswith(("NPC_", "COMFY_", "REDIS_", "SESSION_", "HEALTH_")) or key == "CORS_ORIGINS":
        os.environ.pop(key)
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
with patch("dotenv.load_dotenv", return_value=False):
    from app.main import create_app
    from tests.fakes import FakeLLM, FakeStore


@pytest.fixture(autouse=True)
def forbid_real_http(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("Real HTTP transport is forbidden in unit tests")

    async def forbidden_async(*args, **kwargs):
        forbidden()

    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", forbidden)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, "handle_async_request", forbidden_async)


@pytest.fixture
def backend():
    async def llm_ready():
        pass

    store, llm = FakeStore(), FakeLLM()
    application = create_app(session_store=store, llm_service=llm, llm_probe=llm_ready)
    with TestClient(application, raise_server_exceptions=False) as client:
        yield client, store, llm
    assert store.closed
