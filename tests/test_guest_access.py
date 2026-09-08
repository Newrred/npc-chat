from dataclasses import replace
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from app.errors import ChatError
from app.guest_access import COOKIE, GuestIdentity, GuestLimits
from app.main import create_app
from app.remote_access import RemoteConfig
from app.repository import SQLiteRepository
from tests.fakes import FakeLLM
from app.services.decision_service import LLMTransportError
from scripts.remote_preflight import inspect


CONFIG = RemoteConfig(mode="guest", origin="https://chat.example.com",
                      guest_secret="0123456789abcdef" * 4, daily_total=3, daily_visitor=2)
HEADERS = {"Origin": CONFIG.origin}


def test_guest_cookie_stable_signed_expiring_and_private():
    identity = GuestIdentity(CONFIG.guest_secret)
    owner, cookie = identity.identify("", now=100)
    assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=Lax" in cookie
    raw = cookie.split(";", 1)[0]
    assert identity.identify(raw, now=101) == (owner, None)
    assert identity.identify(raw + "tampered", now=101)[0] != owner
    assert identity.identify(raw, now=100 + 30 * 86400)[0] != owner
    assert GuestIdentity("other" * 20).identify(raw, now=101)[0] != owner


@pytest.mark.parametrize("updates", [{"guest_secret": ""}, {"guest_secret": "x" * 64},
    {"active_visitors": 0}, {"visitor_ttl": 1}, {"daily_total": 0}, {"daily_visitor": 4}])
def test_guest_configuration_limits_required(updates):
    with pytest.raises(ValueError):
        replace(CONFIG, **updates).validate()


def test_visitor_slots_expire_and_same_user_does_not_take_two(tmp_path):
    limits = GuestLimits(tmp_path / "usage.sqlite3", replace(CONFIG, active_visitors=1))
    limits.admit("a", now=100)
    limits.admit("a", now=101)
    with pytest.raises(ChatError) as exc:
        limits.admit("b", now=102)
    assert exc.value.code == "VISITOR_CAPACITY"
    limits.admit("b", now=402)


def test_daily_limits_persist_reset_korean_midnight_and_resist_cookie_rotation(tmp_path):
    path = tmp_path / "usage.sqlite3"
    limits = GuestLimits(path, CONFIG)
    now = 1725688800  # Same fixed date until explicit following-day step.
    limits.admit("a", charge=True, now=now)
    limits.admit("a", charge=True, now=now)
    restarted = GuestLimits(path, CONFIG)
    with pytest.raises(ChatError) as exc:
        restarted.admit("a", charge=True, now=now)
    assert exc.value.code == "DAILY_VISITOR_LIMIT"
    restarted.admit("new-cookie", charge=True, now=now)
    with pytest.raises(ChatError) as exc:
        restarted.admit("another-cookie", charge=True, now=now)
    assert exc.value.code == "DAILY_TOTAL_LIMIT"
    restarted.admit("a", charge=True, now=now + 86400)


def test_daily_total_is_atomic_under_parallel_requests(tmp_path):
    path = tmp_path / "usage.sqlite3"
    limits = GuestLimits(path, replace(CONFIG, active_visitors=20))
    # Initialize schema before concurrent admission.
    limits.admit("setup", now=100)
    def charge(index):
        try:
            GuestLimits(path, replace(CONFIG, active_visitors=20)).admit(str(index), charge=True, now=101)
            return True
        except ChatError:
            return False
    with ThreadPoolExecutor(max_workers=8) as pool:
        assert sum(pool.map(charge, range(12))) == 3


def test_quota_rolls_over_at_korean_midnight(tmp_path):
    limits = GuestLimits(tmp_path / "usage.sqlite3", replace(CONFIG, daily_total=1, daily_visitor=1))
    limits.admit("a", charge=True, now=53999)  # 1970-01-01 23:59:59 KST
    with pytest.raises(ChatError):
        limits.admit("a", charge=True, now=53999)
    limits.admit("a", charge=True, now=54000)  # 1970-01-02 00:00:00 KST


def test_link_opens_without_login_isolates_browsers_and_replays_without_charge(tmp_path):
    repo = SQLiteRepository(tmp_path / "state.sqlite3")
    application = create_app(repository=repo, llm_service=FakeLLM(), remote_config=CONFIG)
    with TestClient(application, base_url=CONFIG.origin) as client:
        page = client.get("/")
        assert page.status_code == 200
        assert COOKIE in page.headers["set-cookie"]
        alice_cookie = client.cookies.get(COOKIE)
        alice = client.post("/api/session", json={}, headers=HEADERS).json()
        assert client.get("/api/ready").status_code == 403
        client.cookies.clear()
        client.get("/")
        bob = client.post("/api/session", json={}, headers=HEADERS).json()
        assert bob["profile_id"] != alice["profile_id"]
        assert client.post("/api/session", json=alice, headers=HEADERS).status_code == 403
        client.cookies.clear()
        client.cookies.set(COOKIE, alice_cookie)
        body = {**alice, "message": "안녕", "client_turn_id": "one"}
        first = client.post("/api/chat", json=body, headers=HEADERS)
        assert first.status_code == 200
        assert client.post("/api/chat", json=body, headers=HEADERS).json() == first.json()
        assert client.post("/api/chat", json={**body, "client_turn_id": "two"}, headers=HEADERS).status_code == 200
        blocked = client.post("/api/chat", json={**body, "client_turn_id": "three"}, headers=HEADERS)
        assert blocked.status_code == 429 and blocked.json()["error"]["code"] == "DAILY_VISITOR_LIMIT"
        assert client.post("/api/chat", json=body, headers=HEADERS).json() == first.json()
        assert repo.load(alice["profile_id"], "default").turn_count == 2


def test_guest_origin_and_host_still_required(tmp_path):
    app = create_app(repository=SQLiteRepository(tmp_path / "state.sqlite3"), llm_service=FakeLLM(),
                     remote_config=CONFIG)
    with TestClient(app, base_url=CONFIG.origin) as client:
        assert client.post("/api/session", json={}).status_code == 403
        assert client.get("/", headers={"Host": "evil.example"}).status_code == 403


def test_failed_generation_consumes_budget_without_saving_turn(tmp_path):
    repo = SQLiteRepository(tmp_path / "state.sqlite3")
    llm = FakeLLM()
    llm.error = LLMTransportError("unavailable")
    app = create_app(repository=repo, llm_service=llm, remote_config=replace(CONFIG, daily_total=1, daily_visitor=1))
    with TestClient(app, base_url=CONFIG.origin) as client:
        client.get("/")
        session = client.post("/api/session", json={}, headers=HEADERS).json()
        body = {**session, "message": "안녕", "client_turn_id": "same"}
        assert client.post("/api/chat", json=body, headers=HEADERS).status_code == 503
        assert client.post("/api/chat", json=body, headers=HEADERS).status_code == 429
        assert len(llm.calls) == 1
        assert repo.load(session["profile_id"], "default").turn_count == 0


def test_guest_preflight_needs_no_access_account(tmp_path):
    model, binary = tmp_path / "model.gguf", tmp_path / "server.exe"
    model.touch()
    binary.touch()
    result = inspect({"NPC_ACCESS_MODE": "guest", "NPC_PUBLIC_ORIGIN": CONFIG.origin,
                      "NPC_GUEST_SECRET": CONFIG.guest_secret,
                      "NPC_DATABASE_PATH": str(tmp_path / "remote.sqlite3"),
                      "NPC_BASE_URL": "http://127.0.0.1:8001/v1", "NPC_MODEL": "test",
                      "LLAMA_MODEL_PATH": str(model), "LLAMA_SERVER_PATH": str(binary),
                      "NPC_TOKEN_COUNT_MODE": "llama_cpp", "COMFY_ENABLED": "false", "COMFY_CONNECT": "false"})
    assert result["configuration_ready"] and not result["release_ready"]
