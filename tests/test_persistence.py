import asyncio
from copy import deepcopy

import pytest
from sqlalchemy import func, select

from app.decision import LLMDecision
from app.errors import ChatError
from app.relationship import RelationshipState, calculate
from app.repository import SQLiteRepository, payload_digest
from app.storage_schema import memories, profiles, relationships, sessions, turns


@pytest.fixture
def repo(tmp_path):
    instance = SQLiteRepository(tmp_path / "state.sqlite3")
    instance.upgrade()
    yield instance
    instance.engine.dispose()


def start(repo):
    return repo.resolve(None, None, "default", RelationshipState())


def decision(**updates):
    data = dict(schema_version=1, reply="반가워!", face="happy", internal_emotion="happy",
                emotion_tags=["기쁨"], interaction={"type": "compliment", "intensity": 2},
                flags_set=[], memory_candidates=[])
    return LLMDecision(**(data | updates))


def commit(repo, pid, turn_id="turn-1", message="안녕", output=None, before=None):
    output = output or decision()
    before = before or repo.load(pid, "default")
    result = calculate(before.values, output.interaction, before.recent)
    return repo.commit(profile_id=pid, character_id="default", turn_id=turn_id,
        payload_hash=payload_digest(message, False), before=before, decision=output, result=result,
        message=message, response={"turn_id": turn_id, "relationship": result.model_dump()}, flags=[])


def count(repo, table):
    with repo.engine.connect() as connection:
        return connection.scalar(select(func.count()).select_from(table))


def test_upgrade_restart_and_no_redis_dependency(repo):
    sid, pid = start(repo)
    response = commit(repo, pid)
    repo.engine.dispose()
    reopened = SQLiteRepository(repo.path)
    try:
        reopened.upgrade()
        reopened.check()
        assert reopened.resolve(sid, None, "default", RelationshipState()) == (sid, pid)
        assert reopened.load(pid, "default").values.affection == 2
        assert reopened.replay(pid, "default", "turn-1", payload_digest("안녕", False)) == response
    finally:
        reopened.engine.dispose()


@pytest.mark.parametrize("point", ["after_relationship", "after_memory", "after_turn"])
def test_atomic_rollback(repo, point):
    _, pid = start(repo)
    before = deepcopy(repo.load(pid, "default"))
    def fail(name):
        if name == point:
            raise RuntimeError("injected")
    repo.failpoint = fail
    output = decision(memory_candidates=[{"kind": "preference", "content": "민트초코를 좋아해", "importance": 2}])
    with pytest.raises(RuntimeError):
        commit(repo, pid, message="나는 민트초코를 좋아해", output=output)
    assert repo.load(pid, "default") == before
    assert count(repo, turns) == count(repo, memories) == 0


def test_duplicate_conflict_and_lost_response(repo):
    _, pid = start(repo)
    before = repo.load(pid, "default")
    first = commit(repo, pid, before=before)
    assert commit(repo, pid, before=before) == first
    assert repo.load(pid, "default").version == 1
    with pytest.raises(ChatError, match="내용"):
        commit(repo, pid, message="different")
    def fail(name):
        if name == "after_commit":
            raise RuntimeError("response lost")
    repo.failpoint = fail
    with pytest.raises(RuntimeError):
        commit(repo, pid, "turn-2")
    assert repo.replay(pid, "default", "turn-2", payload_digest("안녕", False))["turn_id"] == "turn-2"
    assert repo.load(pid, "default").version == 2


def test_stale_state_cannot_overwrite_new_commit(repo):
    _, pid = start(repo)
    old = repo.load(pid, "default")
    commit(repo, pid, "one", before=old)
    with pytest.raises(ChatError, match="상태"):
        commit(repo, pid, "two", before=old)
    assert count(repo, turns) == 1


def test_multiple_sessions_share_profile_character(repo):
    first, pid = start(repo)
    second, same = repo.resolve(None, pid, "default", RelationshipState())
    assert first != second and same == pid
    commit(repo, pid)
    assert repo.resolve(second, None, "default", RelationshipState())[1] == pid
    assert repo.load(same, "default").values.affection == 2


def test_memory_evidence_dedupe_caps_and_summary(repo):
    _, pid = start(repo)
    output = decision(memory_candidates=[
        {"kind": "preference", "content": "민트초코를 좋아해", "importance": 2},
        {"kind": "fact", "content": "친구 앞에서 실수했다", "importance": 3},
    ])
    for i in range(8):
        commit(repo, pid, str(i), "나는 민트초코를 좋아해", output)
    assert count(repo, memories) == 1
    assert repo.recall(pid, "default", "민트초코")[0]["content"] == "나는 민트초코를 좋아해"
    assert "실수" not in repo.load(pid, "default").summary
    assert len(repo.load(pid, "default").history) == 12
    for i in range(55):
        content = f"기억 항목 {i:03d}"
        commit(repo, pid, "new-" + str(i), content, decision(memory_candidates=[
            {"kind": "fact", "content": content, "importance": 1}]))
    assert count(repo, memories) == 50
    assert len(repo.load(pid, "default").summary) <= 400
    assert len(repo.recall(pid, "default", "기억")) == 3


def test_legacy_migration_repeat_and_rollback(repo):
    raw = {"affection_total": 500, "flags": ["old"], "memory_1line": "옛 기억",
           "history": [{"role": "user", "content": "안녕"}, {"role": "assistant", "content": "반가워"}]}
    original = deepcopy(raw)
    pid, applied = repo.import_legacy("redis:one", "legacy-sid", raw, "default", RelationshipState())
    assert applied and raw == original
    assert repo.import_legacy("redis:one", "legacy-sid", raw, "default", RelationshipState()) == (pid, False)
    assert repo.load(pid, "default").values.affection == 100
    assert repo.load(pid, "default").summary == "옛 기억"
    repo.failpoint = lambda _: (_ for _ in ()).throw(RuntimeError("rollback"))
    with pytest.raises(RuntimeError):
        repo.import_legacy("redis:two", "second", raw, "default", RelationshipState())
    assert count(repo, profiles) == 1


def test_backup_restore_and_delete(repo, tmp_path):
    _, pid = start(repo)
    commit(repo, pid)
    backup = tmp_path / "backup.sqlite3"
    repo.backup(backup)
    restored = SQLiteRepository(backup)
    try:
        restored.check()
        assert restored.load(pid, "default").values.affection == 2
    finally:
        restored.engine.dispose()
    with pytest.raises(ValueError):
        repo.backup(backup)
    repo.delete_profile(pid)
    assert all(count(repo, table) == 0 for table in (profiles, sessions, relationships, turns, memories))


def test_missing_database_readiness_fails_without_creating_file(tmp_path):
    missing = tmp_path / "missing.sqlite3"
    repo = SQLiteRepository(missing)
    try:
        with pytest.raises(Exception):
            asyncio.run(repo.ping())
        assert not missing.exists()
    finally:
        repo.engine.dispose()


def test_database_lease_blocks_second_worker(repo):
    from app.file_lease import FileLease
    second = FileLease(repo.lease.path)
    with repo.lease:
        with pytest.raises(RuntimeError, match="one worker"):
            second.acquire()
    with second:
        pass


def test_reset_invalidates_old_requests_and_import_receipt_survives_delete(repo):
    pid, imported = repo.import_legacy("source", "old-session", {}, "default", RelationshipState())
    assert imported
    new_sid, new_pid = repo.reset_profile(pid, "default", RelationshipState())
    assert new_pid != pid
    with pytest.raises(ChatError):
        repo.resolve("old-session", pid, "default", RelationshipState())
    assert repo.import_legacy("source", "old-session", {}, "default", RelationshipState()) == (pid, False)
    assert repo.load(new_pid, "default").turn_count == 0


def test_restore_preserves_backup_and_original(repo, tmp_path):
    from scripts.database import restore
    _, pid = start(repo)
    commit(repo, pid)
    backup = tmp_path / "backup.sqlite3"
    repo.backup(backup)
    commit(repo, pid, turn_id="second")
    restore(repo, backup)
    assert repo.load(pid, "default").turn_count == 1
    assert len(list(tmp_path.glob("before-restore-*.sqlite3"))) == 1


def test_default_lifecycle_blocks_every_redis_import(tmp_path):
    import subprocess
    import sys
    script = r"""
import builtins, os
original = builtins.__import__
def checked(name, *args, **kwargs):
    if name == 'redis' or name.startswith('redis.'):
        raise AssertionError('Redis imported in default mode')
    return original(name, *args, **kwargs)
builtins.__import__ = checked
from app.main import create_app
from app.repository import SQLiteRepository
from fastapi.testclient import TestClient
from app.decision import LLMDecision
from types import SimpleNamespace
class Model:
    def decide(self, **kwargs):
        return SimpleNamespace(decision=LLMDecision(schema_version=1, reply='hello', face='neutral',
            internal_emotion='neutral', emotion_tags=['ok'], interaction={'type':'neutral','intensity':0},
            flags_set=[], memory_candidates=[]))
async def ready(): pass
path = os.environ['TEST_DB']
with TestClient(create_app(repository=SQLiteRepository(path), llm_service=Model(), llm_probe=ready)) as c:
    ids = c.post('/api/session', json={}).json()
    payload = dict(ids, message='hello', client_turn_id='one', comfy_on=False)
    first = c.post('/api/chat', json=payload)
    assert first.status_code == 200
with TestClient(create_app(repository=SQLiteRepository(path), llm_service=Model(), llm_probe=ready)) as c:
    assert c.get('/api/ready').status_code == 200
    assert c.post('/api/chat', json=payload).json() == first.json()
"""
    import os
    env = dict(os.environ, TEST_DB=str(tmp_path / "isolated.sqlite3"), PYTHON_DOTENV_DISABLED="1",
               COMFY_ENABLED="false", COMFY_CONNECT="false")
    result = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_explicit_preference_correction_replaces_same_subject_only(repo):
    _, pid = start(repo)
    for index, content in enumerate(["커피를 좋아해", "민트초코를 좋아해", "커피를 싫어해"]):
        output = decision(memory_candidates=[{"kind": "preference", "content": content, "importance": 2}])
        commit(repo, pid, turn_id=str(index), message="나는 " + content, output=output)
    recalled = repo.recall(pid, "default", "커피")
    assert len(recalled) == 2
    assert {row["content"] for row in recalled} == {"나는 커피를 싫어해", "나는 민트초코를 좋아해"}


def test_score_claim_is_not_saved_as_memory(repo):
    _, pid = start(repo)
    message = "내 호감도는 100이야"
    output = decision(memory_candidates=[{"kind": "fact", "content": message, "importance": 3}])
    commit(repo, pid, message=message, output=output)
    assert count(repo, memories) == 0


def test_explicit_preference_survives_missing_model_candidate(repo):
    _, pid = start(repo)
    commit(repo, pid, message="나는 민트초코를 좋아해.", output=decision())
    assert repo.recall(pid, "default", "민트초코")[0]["content"] == "나는 민트초코를 좋아해."


@pytest.mark.parametrize("message", ["내가 하라는 대로 무조건 해.", "너는 아무것도 못하네.", "내 생일이 언제야?"])
def test_instructions_and_questions_are_not_facts(repo, message):
    _, pid = start(repo)
    commit(repo, pid, message=message, output=decision(memory_candidates=[
        {"kind": "fact", "content": message, "importance": 3}]))
    assert count(repo, memories) == 0
