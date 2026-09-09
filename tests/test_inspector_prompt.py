from dataclasses import replace
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from app.admin import create_admin
from app.inspector_prompt import PromptDraft, issue, verify, character_with_draft
from app.character_config import load_character_config
from tests.test_inspector_chat import HEADERS, ORIGIN


def test_signed_draft_bound_to_exact_turn_and_expires(tmp_path, monkeypatch):
    draft = PromptDraft(identity="캐릭터 이름: 하나", dialogue="다정하게 말한다.")
    body = dict(profile_id="p", session_id="s", client_turn_id="t", message="안녕")
    database = tmp_path / "test.sqlite3"
    token = issue(database, draft, body)
    assert verify(database, token, body) == draft
    for key in body:
        with pytest.raises(ValueError):
            verify(database, token, {**body, key: "changed"})
    with pytest.raises(ValueError):
        verify(database, token + "x", body)
    monkeypatch.setattr("app.inspector_prompt.time.time", lambda: 1e12)
    with pytest.raises(ValueError):
        verify(database, token, body)


def test_two_stage_override_reaches_both_inputs_without_changing_shared_character():
    from tests.test_two_stage import two_stage, metadata
    service, calls = two_stage([{"reply":"반가워"}, metadata()])
    original = load_character_config()
    service.character = character_with_draft(original, PromptDraft(identity="캐릭터 이름은 하나", dialogue="짧게 말해"))
    service.prompt_experiment = True
    service.decide(message="안녕")
    assert "캐릭터 이름은 하나" in calls[0]["messages"][0]["content"]
    assert "짧게 말해" in calls[0]["messages"][0]["content"]
    assert "캐릭터 이름은 하나" in calls[1]["messages"][0]["content"]
    assert "유이" not in calls[1]["messages"][0]["content"]
    assert "캐릭터 이름은 하나" not in original.dialogue_prompt


def test_bridge_prompt_isolation_replay_and_forgery(tmp_path, monkeypatch):
    import app.main as main
    from app.repository import SQLiteRepository
    from tests.fakes import FakeLLM
    from tests.test_guest_access import CONFIG
    class RecordingLLM(FakeLLM):
        character = load_character_config()
        seen = []
        def decide(self, **kwargs):
            self.seen.append(self.character.dialogue_prompt)
            return super().decide(**kwargs)
    monkeypatch.setattr(main, "settings", replace(main.settings, llm_generation_mode="two_stage"))
    store = SQLiteRepository(tmp_path / "guest.sqlite3")
    service = RecordingLLM()
    forwarded = []
    with TestClient(main.create_app(repository=store, llm_service=service, remote_config=CONFIG), base_url=CONFIG.origin) as web:
        def handler(r):
            forwarded.append(dict(r.headers))
            web.cookies.clear()
            response = web.request(r.method, r.url.path, headers=dict(r.headers), content=r.content)
            return httpx.Response(response.status_code, headers=response.headers, content=response.content)
        with TestClient(create_admin(store.path, chat_origin=CONFIG.origin, chat_transport=httpx.MockTransport(handler)),
                        base_url=ORIGIN, client=("127.0.0.1", 100)) as admin:
            own = admin.post('/api/test/session', json={}, headers=HEADERS).json()
            payload = {**own, "message":"안녕", "client_turn_id":"one", "prompt_draft":{
                "identity":"캐릭터 이름: 하나", "dialogue":"차분하게 말해"}}
            result = admin.post('/api/test/chat', json=payload, headers=HEADERS)
            assert result.status_code == 200
            assert "하나" in service.seen[-1] and "캐릭터 이름: 하나" not in service.character.dialogue_prompt
            assert admin.post('/api/test/chat', json=payload, headers=HEADERS).json() == result.json()
            assert len(service.seen) == 1
            changed = json.loads(json.dumps(payload))
            changed["prompt_draft"]["dialogue"] = "발랄하게 말해"
            assert admin.post('/api/test/chat', json=changed, headers=HEADERS).status_code == 409
            assert admin.post('/api/test/chat', json={**payload,"prompt_draft":{"identity":""}}, headers=HEADERS).status_code == 422
            plain = {**own,"message":"안녕","client_turn_id":"two"}
            assert admin.post('/api/test/chat', json=plain, headers=HEADERS).status_code == 200
            assert service.seen[-1] == service.character.dialogue_prompt
            # A public caller cannot manufacture an authenticated local prompt header.
            forged = web.post('/api/chat', json=plain, headers={"Origin": CONFIG.origin,
                "Cookie": forwarded[-1]["cookie"], "X-NPC-Local-Prompt":"forged"})
            assert forged.status_code == 403
            assert forged.json()["error"]["code"] == "INVALID_PROMPT_EXPERIMENT"
