from copy import deepcopy
from tempfile import TemporaryDirectory
from pathlib import Path
from types import SimpleNamespace

from sqlalchemy import select

from app.repository import SQLiteRepository
from app.storage_schema import sessions
from app.decision import LLMDecision
from app.services.decision_service import DecisionResult


class FakeStore(SQLiteRepository):
    """Isolated actual SQLite storage with explicit dependency failure seams."""
    def __init__(self):
        self.temporary = TemporaryDirectory()
        super().__init__(Path(self.temporary.name) / "test.sqlite3")
        self.upgrade()
        self.saved = []
        self.closed = False
        self.ping_error = None
        self.lock_error = None

    @property
    def states(self):
        with self.engine.connect() as connection:
            rows = connection.execute(select(sessions)).mappings().all()
        output = {}
        for row in rows:
            state = super().load(row["profile_id"], row["character_id"])
            output[row["id"]] = SimpleNamespace(affection_total=state.values.affection,
                flags=state.flags, memory_1line=state.summary, history=state.history)
        return output

    async def ping(self):
        if self.ping_error:
            raise self.ping_error
        await super().ping()

    def load(self, *args):
        if self.lock_error:
            raise self.lock_error
        return super().load(*args)

    def commit(self, **kwargs):
        result = super().commit(**kwargs)
        self.saved.append(result["session_id"])
        return result

    async def close(self):
        await super().close()
        self.closed = True
        self.temporary.cleanup()


class FakeLLM:
    def __init__(self):
        self.calls = []
        self.error = None
        self.response = {
            "reply": "오늘도 와 줬네. 반가워.",
            "face": "shy smile",
            "internal_emotion": "happy",
            "affection_delta": 2,
            "tags": ["기쁨"],
            "flags_set": [],
            "memory_1line": "유저:오늘도인사하러왔음|NPC감정:happy",
        }

    def chat(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        if self.error:
            raise self.error
        return deepcopy(self.response)



    def decide(self, **kwargs):
        self.calls.append(deepcopy(kwargs))
        if self.error:
            raise self.error
        decision = LLMDecision(schema_version=1, reply=self.response["reply"], face=self.response["face"],
            internal_emotion=self.response["internal_emotion"], emotion_tags=self.response["tags"],
            flags_set=self.response["flags_set"], interaction={"type": "compliment", "intensity": 2},
            memory_candidates=[])
        return DecisionResult(decision, 1, 0, 0, 50, 0.01)
