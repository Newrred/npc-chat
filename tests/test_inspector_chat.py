import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.admin import create_admin
from app.inspector_chat import LOCAL_COOKIE

ORIGIN = "http://127.0.0.1:8002"
HEADERS = {"Origin": ORIGIN}


def client(tmp_path, handler, enabled=True):
    return TestClient(create_admin(tmp_path / "unused", chat_origin="https://chat.example.com" if enabled else None,
        chat_transport=httpx.MockTransport(handler)), base_url=ORIGIN, client=("127.0.0.1", 123))


def test_fixed_loopback_route_cookie_isolation_and_exact_payload(tmp_path):
    calls = []
    def handle(request):
        calls.append(request)
        if request.url.path == "/api/session":
            return httpx.Response(200, json={"session_id": "s", "profile_id": "p"},
                headers={"set-cookie": "__Host-npc_guest=abc.123.sig; Secure; HttpOnly; Path=/"})
        return httpx.Response(200, json={"reply": "test"})
    with client(tmp_path, handle) as c:
        response = c.post("/api/test/session", json={"profile_id": "foreign"}, headers=HEADERS)
        assert response.status_code == 200 and "HttpOnly" in response.headers["set-cookie"]
        assert "SameSite=strict" in response.headers["set-cookie"]
        c.post("/api/test/chat", json={"session_id": "s", "profile_id": "p", "message": "hello",
            "client_turn_id": "same", "history": ["forged"], "url": "https://evil.example"}, headers=HEADERS)
        assert json.loads(calls[0].content) == {}
        assert json.loads(calls[1].content) == dict(session_id="s", profile_id="p", message="hello", client_turn_id="same")
        assert calls[1].url.host == "127.0.0.1" and calls[1].url.port == 8000
        assert calls[1].headers["host"] == "chat.example.com" and calls[1].headers["origin"] == "https://chat.example.com"
        assert calls[1].headers["cookie"] == "__Host-npc_guest=abc.123.sig"
        assert "authorization" not in calls[1].headers
        assert LOCAL_COOKIE not in str(calls[1].headers)
    with client(tmp_path, handle) as other:
        other.post("/api/test/session", json={}, headers=HEADERS)
        assert "cookie" not in calls[-1].headers


@pytest.mark.parametrize("headers", [{}, {"Origin":"https://evil.example"},
    {"Origin":ORIGIN,"Sec-Fetch-Site":"cross-site"}, {"Origin":ORIGIN,"Host":"evil.example"}])
def test_write_boundary(tmp_path, headers):
    def forbidden(_):
        pytest.fail("must not contact web")
    with client(tmp_path, forbidden) as c:
        assert c.post("/api/test/chat", json={}, headers=headers).status_code == 403


def test_routes_body_errors_and_backend_failures(tmp_path):
    def handler(r):
        return httpx.Response(429, json={"error":{"code":"DAILY_TOTAL_LIMIT","message":"quota"}})
    with client(tmp_path, handler) as c:
        assert c.post("/api/test/chat", content="no", headers=HEADERS).status_code == 403
        assert c.post("/api/test/chat", content="{", headers={**HEADERS,"Content-Type":"application/json"}).status_code == 400
        assert c.post("/api/test/chat", json={"message":"x"*17000}, headers=HEADERS).status_code == 413
        assert c.post("/api/test/evil", json={}, headers=HEADERS).status_code == 403
        assert c.get("/api/test/chat").status_code == 404
        assert c.post("/api/test/chat", json={}, headers=HEADERS).status_code == 429
    def outage(r):
        raise httpx.ConnectError("private diagnostic", request=r)
    with client(tmp_path, outage) as c:
        response=c.post("/api/test/chat",json={},headers=HEADERS)
        assert response.status_code==503 and "private" not in response.text
    with client(tmp_path, handler, enabled=False) as c:
        assert c.post("/api/test/session",json={},headers=HEADERS).status_code==403


def test_guest_ownership_replay_and_quota_through_bridge(tmp_path):
    from app.main import create_app
    from app.repository import SQLiteRepository
    from tests.fakes import FakeLLM
    from tests.test_guest_access import CONFIG
    store=SQLiteRepository(tmp_path / "guest.sqlite3")
    with TestClient(create_app(repository=store,llm_service=FakeLLM(),remote_config=CONFIG),base_url=CONFIG.origin) as web:
        def handler(r):
            web.cookies.clear()
            result = web.request(r.method, r.url.path + ("?"+r.url.query.decode() if r.url.query else ""),
                headers=dict(r.headers),content=r.content)
            return httpx.Response(result.status_code, headers=result.headers, content=result.content)
        with client(tmp_path,handler) as a,client(tmp_path,handler) as b:
            first=a.post('/api/test/session',json={},headers=HEADERS).json()
            second=b.post('/api/test/session',json={},headers=HEADERS).json()
            assert first['profile_id']!=second['profile_id']
            payload={**first,'message':'hello','client_turn_id':'same'}
            r=a.post('/api/test/chat',json=payload,headers=HEADERS)
            assert r.status_code==200
            assert a.post('/api/test/chat',json=payload,headers=HEADERS).json()==r.json()
            assert b.post('/api/test/chat',json=payload,headers=HEADERS).status_code==403
            assert a.get('/api/test/conversation',params=first).json()['items'][0]['reply']==r.json()['reply']
            assert a.post('/api/test/chat',json={**payload,'client_turn_id':'second'},headers=HEADERS).status_code==200
            limited=a.post('/api/test/chat',json={**payload,'client_turn_id':'third'},headers=HEADERS)
            assert limited.status_code==429 and limited.json()['error']['code']=='DAILY_VISITOR_LIMIT'
            assert a.post('/api/test/chat',json=payload,headers=HEADERS).json()==r.json()
            assert a.post('/api/test/reset',json=first,headers=HEADERS).status_code==200
