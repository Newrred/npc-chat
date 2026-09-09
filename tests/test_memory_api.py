import sqlite3

from app.decision import MemoryCandidate
from app.services.decision_service import LLMTransportError
from tests.test_decision import service, valid
from tests.test_persistence import decision
from app.relationship import calculate
from app.repository import SQLiteRepository, payload_digest


def seed(store, pid, text, turn="seed", kind="fact"):
    output = decision(memory_candidates=[dict(kind=kind, content=text, importance=2)])
    before = store.load(pid, "default")
    SQLiteRepository.commit(store, profile_id=pid, character_id="default", turn_id=turn,
        message=text, decision=output, before=before, payload_hash=payload_digest(text, False),
        result=calculate(before.values, output.interaction, before.recent), flags=[],
        response={"turn_id": turn, "reply": output.reply})


def test_api_uses_server_history_and_never_browser_or_other_owner_history(backend):
    client, store, llm = backend
    ids = client.post("/api/session", json={}).json()
    other = client.post("/api/session", json={}).json()
    seed(store, ids["profile_id"], "나는 고양이 보리를 키워.")
    seed(store, other["profile_id"], "나는 보리를 싫어해.", kind="preference")
    payload = dict(ids, message="걔 때문에 잠을 못 잤어", client_turn_id="followup",
                   history=[dict(role="user", content="커피를 좋아해")])
    response = client.post("/api/chat", json=payload)
    assert response.status_code == 200
    assert llm.calls[-1]["memories"] == [dict(content="나는 고양이 보리를 키워.", kind="fact")]
    client.post("/api/chat", json={**ids, "message": "오늘 점심 뭐 먹지?", "client_turn_id": "shift"})
    assert llm.calls[-1]["memories"] == []
    assert len(llm.calls) == 2


def test_same_turn_transport_has_no_stale_preference_and_replay_is_atomic(backend):
    client, store, _ = backend
    ids = client.post("/api/session", json={}).json()
    seed(store, ids["profile_id"], "나는 커피를 좋아해.", kind="preference")
    seed(store, ids["profile_id"], "나는 민트초코를 좋아해.", turn="other", kind="preference")
    adapter, calls = service([valid()])
    client.app.state.llm_service = adapter
    try:
        payload = {**ids, "message": "이제 커피 싫어해", "client_turn_id": "correct"}
        response = client.post("/api/chat", json=payload)
        assert response.status_code == 200
        assert "나는 커피를 좋아해" not in str(calls[0]["messages"])
        assert calls[0]["messages"][-1]["content"] == payload["message"]
        assert client.post("/api/chat", json=payload).json() == response.json()
        assert len(calls) == 1
        assert store.recall(ids["profile_id"], "default", "커피")[0]["content"] == payload["message"]
        assert store.recall(ids["profile_id"], "default", "민트초코")[0]["content"] == "나는 민트초코를 좋아해."
    finally:
        adapter.client.close()


def test_failed_model_or_commit_cannot_replace_preference(backend):
    client, store, llm = backend
    ids = client.post("/api/session", json={}).json()
    seed(store, ids["profile_id"], "나는 커피를 좋아해.", kind="preference")
    before = store.load(ids["profile_id"], "default")
    payload = {**ids, "message": "이제 커피 싫어해", "client_turn_id": "correct"}
    llm.error = LLMTransportError("synthetic")
    assert client.post("/api/chat", json=payload).status_code == 503
    llm.error = None
    def fail(point):
        if point == "after_memory":
            raise sqlite3.OperationalError("synthetic")
    store.failpoint = fail
    assert client.post("/api/chat", json=payload).status_code == 503
    assert store.load(ids["profile_id"], "default") == before
    assert store.recall(ids["profile_id"], "default", "커피")[0]["content"] == "나는 커피를 좋아해."


def test_foreign_preference_does_not_replace_users_preference(backend):
    client, store, llm = backend
    ids = client.post("/api/session", json={}).json()
    seed(store, ids["profile_id"], "나는 커피를 좋아해.", kind="preference")
    original = llm.decide
    def wrong_candidate(**kwargs):
        generated = original(**kwargs)
        generated.decision.memory_candidates = [MemoryCandidate(kind="preference", content="커피를 싫어해", importance=3)]
        return generated
    llm.decide = wrong_candidate
    assert client.post("/api/chat", json={**ids, "message": "민지는 커피를 싫어해", "client_turn_id": "other"}).status_code == 200
    assert store.recall(ids["profile_id"], "default", "커피")[0]["content"] == "나는 커피를 좋아해."
