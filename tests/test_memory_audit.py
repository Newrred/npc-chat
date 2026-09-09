import pytest

from app.memory import accepted_candidates, retrieve
from app.decision import MemoryCandidate
from app.debug_trace import read


@pytest.mark.parametrize("message", ["나는 커피를 좋아해.", "내 이름은 민석이야.", "커피 좋아했지?", "안녕", "나는 커피를 싫어해."])
def test_candidate_audit_preserves_acceptance_and_reports_reasons(message):
    candidates = [MemoryCandidate(kind="fact", content="내 이름은 민석이야.", importance=2),
                  MemoryCandidate(kind="preference", content="나는 커피를 좋아해.", importance=2)]
    audit = []
    assert accepted_candidates(candidates, message, audit) == accepted_candidates(candidates, message)
    assert audit and all(item["reason"] for item in audit)
    if message == "나는 커피를 좋아해.":
        assert audit[-1]["origin"] == "server_preference_rule" and audit[-1]["accepted"]
    if "?" in message:
        assert all(not item.get("accepted") for item in audit)


def test_retrieval_audit_explains_continuation_and_contradiction():
    rows = [dict(key="coffee", kind="preference", content="나는 커피를 좋아해.", updated=1, importance=2)]
    audit = {}
    history = [dict(role="user", content="커피가 맛있어")]
    assert retrieve(rows, "응", history, audit) == retrieve(rows, "응", history)
    assert "가장 가까운" in audit["method"] and audit["considered"][0]["selected"]
    assert retrieve(rows, "나는 커피를 싫어해.", audit=audit) == []
    assert audit["considered"][0]["contradicted"]


def test_commit_audit_is_after_success_and_includes_server_derived_memory(backend, monkeypatch):
    from app.main import settings
    client, store, _ = backend
    monkeypatch.setattr(settings, "debug_trace", True)
    ids = client.post('/api/session', json={}).json()
    assert client.post('/api/chat', json={**ids,"message":"내 이름은 민석이야.","client_turn_id":"ok"}).status_code == 200
    events = read(store.path)[0]["events"]
    result = next(e for e in events if e["event"] == "memory_committed")
    assert result["derived_profile_updates"] == {"name":"민석"}
    assert events[-1]["event"] == "completed"
    def failure(point):
        if point == "after_memory":
            raise RuntimeError("synthetic rollback")
    store.failpoint = failure
    assert client.post('/api/chat', json={**ids,"message":"안녕","client_turn_id":"fail"}).status_code == 500
    failed = next(t for t in read(store.path) if t["turn_id"] == "fail")
    assert not any(e["event"] == "memory_committed" for e in failed["events"])
