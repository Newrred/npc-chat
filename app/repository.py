"""Short SQLite transactions. Never keep a transaction open during inference."""
from dataclasses import dataclass
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from typing import Protocol
import uuid

from fastapi.concurrency import run_in_threadpool
from sqlalchemy import create_engine, delete, event, insert, select, update
from sqlalchemy.engine import URL

from app.conversation_memory import source_views
from app.decision import Interaction
from app.debug_trace import forget
from app.errors import ChatError, conflict
from app.file_lease import FileLease
from app.memory import accepted_candidates, memory_subject, retrieve, rolling_summary
from app.relationship import DIMENSIONS, RelationshipState, from_legacy
from app.storage_schema import imports, memories, profiles, relationships, sessions, turns


@dataclass
class Snapshot:
    values: RelationshipState
    flags: list
    summary: str
    history: list
    recent: list[Interaction]
    version: int
    turn_count: int


class ChatRepository(Protocol):
    def resolve(self, session_id, profile_id, character_id, defaults, *, allow_stale=False): ...
    def load(self, profile_id, character_id) -> Snapshot: ...
    def replay(self, profile_id, character_id, turn_id, payload_hash): ...
    def commit(self, **kwargs): ...
    def recall(self, profile_id, character_id, query, history=None): ...
    async def ping(self): ...
    async def close(self): ...


def payload_digest(message, comfy_on):
    return hashlib.sha256(json.dumps([message, comfy_on], ensure_ascii=False).encode()).hexdigest()


class SQLiteRepository:
    def __init__(self, path, *, failpoint=None):
        self.path = Path(path).resolve()
        if str(path).startswith(("\\\\", "//")):
            raise ValueError("SQLite requires a local disk path")
        self.engine = create_engine(URL.create("sqlite", database=str(self.path)),
                                    connect_args={"check_same_thread": False, "timeout": 5})
        self.failpoint = failpoint or (lambda _: None)
        self.lease = FileLease(self.path.with_suffix(".owner.lock"))

        @event.listens_for(self.engine, "connect")
        def pragmas(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")

    def upgrade(self):
        from alembic import command
        from alembic.config import Config
        self.path.parent.mkdir(parents=True, exist_ok=True)
        cfg = Config()
        cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "migrations"))
        with self.engine.begin() as connection:
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
        with self.engine.connect() as connection:
            connection.exec_driver_sql("PRAGMA journal_mode=WAL")

    async def ping(self):
        await run_in_threadpool(self.check)

    def check(self):
        # mode=rw prevents readiness from silently creating a missing database.
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=rw", uri=True, timeout=2)) as connection:
            if connection.execute("SELECT version_num FROM alembic_version").fetchone() != ("0001",):
                raise RuntimeError("Database schema is not ready")
            connection.execute("SELECT id FROM profiles LIMIT 1").fetchone()

    async def close(self):
        await run_in_threadpool(self.engine.dispose)
        self.lease.release()

    @staticmethod
    def _where(table, profile_id, character_id):
        return (table.c.profile_id == profile_id) & (table.c.character_id == character_id)

    def history_page(self, profile_id, character_id, before=None, limit=50):
        where = self._where(turns, profile_id, character_id)
        with self.engine.connect() as connection:
            if before:
                cursor = connection.execute(select(turns.c.created).where(
                    where & (turns.c.client_turn_id == before))).first()
                if not cursor:
                    raise ChatError("HISTORY_CHANGED", "대화가 변경되었습니다. 새로고침해 주세요.", 409)
                where &= ((turns.c.created < cursor.created) | (
                    (turns.c.created == cursor.created) & (turns.c.client_turn_id < before)))
            rows = connection.execute(select(turns).where(where).order_by(
                turns.c.created.desc(), turns.c.client_turn_id.desc()).limit(limit + 1)).mappings().all()
        page = rows[:limit]
        return {"items": [{"turn_id": row["client_turn_id"], "user_message": row["user_message"],
                           "reply": row["response"]["reply"], "face": row["response"].get("face", "neutral"),
                           "created": row["created"]} for row in reversed(page)],
                "before": page[-1]["client_turn_id"] if len(rows) > limit else None}

    def reset_conversation(self, session_id, profile_id, character_id, defaults):
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            valid = connection.execute(select(sessions.c.id).where(
                self._where(sessions, profile_id, character_id) & (sessions.c.id == session_id))).first()
            if not valid:
                raise ChatError("SESSION_NOT_FOUND", "이미 종료된 대화입니다. 새로고침해 주세요.", 404)
            for table in (turns, memories, sessions):
                connection.execute(delete(table).where(self._where(table, profile_id, character_id)))
            connection.execute(update(relationships).where(self._where(relationships, profile_id, character_id))
                .values(**defaults.model_dump(), flags=[], summary="", history=[], recent=[], turn_count=0,
                        version=relationships.c.version + 1))
            self.failpoint("after_reset")
        forget(self.path, profile_id, character_id)
        return {"closed": True}

    def resolve(self, session_id, profile_id, character_id, defaults, *, allow_stale=False):
        with self.engine.begin() as connection:
            if session_id:
                row = connection.execute(select(sessions).where(sessions.c.id == session_id)).mappings().first()
                if row:
                    if profile_id and row["profile_id"] != profile_id:
                        raise ChatError("SESSION_PROFILE_CONFLICT", "대화와 프로필이 일치하지 않습니다.")
                    if row["character_id"] != character_id:
                        raise ChatError("CHARACTER_CONFLICT", "다른 캐릭터의 대화입니다.")
                    return session_id, row["profile_id"]
                if not allow_stale:
                    raise ChatError("SESSION_NOT_FOUND", "저장된 대화를 찾을 수 없습니다.", 404)
            if profile_id:
                if not connection.execute(select(profiles.c.id).where(profiles.c.id == profile_id)).first():
                    raise ChatError("PROFILE_NOT_FOUND", "프로필을 찾을 수 없습니다.", 404)
            else:
                profile_id = uuid.uuid4().hex
                connection.execute(insert(profiles).values(id=profile_id, created=time.time()))
            where = self._where(relationships, profile_id, character_id)
            if not connection.execute(select(relationships.c.version).where(where)).first():
                self._new_relationship(connection, profile_id, character_id, defaults)
            session_id = uuid.uuid4().hex
            connection.execute(insert(sessions).values(id=session_id, profile_id=profile_id, character_id=character_id))
            return session_id, profile_id

    @staticmethod
    def _new_relationship(connection, profile_id, character_id, defaults, **extra):
        values = {"profile_id": profile_id, "character_id": character_id, **defaults.model_dump(),
                  "flags": [], "summary": "", "history": [], "recent": [], "version": 0, "turn_count": 0}
        connection.execute(insert(relationships).values(**(values | extra)))

    def resolve_owned(self, owner, session_id, profile_id, character_id, defaults, *, create=False):
        """Remote profiles are derived only from verified issuer/subject, never claimed by a browser."""
        expected = hashlib.sha256(("remote-profile-v1\0" + owner).encode()).hexdigest()
        if profile_id and profile_id != expected:
            raise ChatError("ACCESS_DENIED", "이 대화에 접근할 수 없습니다.", 403)
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            if session_id:
                row = connection.execute(select(sessions).where(sessions.c.id == session_id)).mappings().first()
                if not row or row["profile_id"] != expected or row["character_id"] != character_id:
                    raise ChatError("ACCESS_DENIED", "이 대화에 접근할 수 없습니다.", 403)
                return session_id, expected
            if not create:
                raise ChatError("SESSION_REQUIRED", "먼저 대화 세션을 생성해 주세요.", 422)
            if not connection.execute(select(profiles.c.id).where(profiles.c.id == expected)).first():
                connection.execute(insert(profiles).values(id=expected, created=time.time()))
            where = self._where(relationships, expected, character_id)
            if not connection.execute(select(relationships.c.version).where(where)).first():
                self._new_relationship(connection, expected, character_id, defaults)
            # Reopening a browser reuses the account's session instead of accumulating empty rows.
            existing = connection.execute(select(sessions.c.id).where(
                sessions.c.profile_id == expected, sessions.c.character_id == character_id)).scalar()
            sid = existing or uuid.uuid4().hex
            if not existing:
                connection.execute(insert(sessions).values(id=sid, profile_id=expected, character_id=character_id))
            return sid, expected

    def load(self, profile_id, character_id):
        with self.engine.connect() as connection:
            row = connection.execute(select(relationships).where(
                self._where(relationships, profile_id, character_id))).mappings().one()
            committed = connection.execute(select(turns.c.user_message, turns.c.decision).where(
                self._where(turns, profile_id, character_id)).order_by(
                turns.c.created, turns.c.client_turn_id)).mappings().all()
        history = [{"role": role, "content": content} for turn in committed
                   for role, content in (("user", turn["user_message"]), ("assistant", turn["decision"]["reply"]))]
        # Preserve any legacy-only prefix while it still exists in the compatibility cache.
        if len(history) < len(row["history"]):
            history = row["history"][:len(row["history"]) - len(history)] + history
        return Snapshot(RelationshipState(**{key: row[key] for key in DIMENSIONS}), row["flags"], row["summary"],
                        history, [Interaction.model_validate(value) for value in row["recent"]],
                        row["version"], row["turn_count"])

    def replay(self, profile_id, character_id, turn_id, payload_hash):
        with self.engine.connect() as connection:
            row = connection.execute(select(turns).where(self._where(turns, profile_id, character_id),
                                     turns.c.client_turn_id == turn_id)).mappings().first()
        if row:
            if row["payload_hash"] != payload_hash:
                raise conflict()
            return row["response"]
        return None

    def recall(self, profile_id, character_id, query, history=None):
        from app.debug_trace import current, emit
        auditing = current.get() is not None
        derived_audit, stored_audit = ({}, {}) if auditing else (None, None)
        with self.engine.connect() as connection:
            rows = connection.execute(select(memories).where(
                self._where(memories, profile_id, character_id))).mappings().all()
            sources = connection.execute(select(turns.c.client_turn_id, turns.c.user_message, turns.c.decision).where(
                self._where(turns, profile_id, character_id)).order_by(
                turns.c.created, turns.c.client_turn_id)).mappings()
            derived = source_views(sources, query, history, audit=derived_audit)
        retrieved = retrieve(rows, query, history, audit=stored_audit)
        emit("memory_retrieval", user_message=query, derived=derived_audit, stored=stored_audit)
        return derived + retrieved

    def commit(self, *, profile_id, character_id, turn_id, payload_hash, before, decision, result,
               message, response, flags):
        # Validate all external values before touching durable state.
        values = RelationshipState.model_validate(result.values).model_dump()
        from app.debug_trace import current, emit
        from app.conversation_memory import profile_updates, dialogue_events
        memory_audit = [] if current.get() is not None else None
        accepted = accepted_candidates(decision.memory_candidates, message, audit=memory_audit)
        history = before.history + [{"role": "user", "content": message},
                                    {"role": "assistant", "content": decision.reply}]
        summary = rolling_summary(before.summary, history[-14:-12])
        response = dict(response, memory={**response.get("memory", {}), "summary_updated": summary != before.summary,
                                         "accepted_candidates": len(accepted)}, memory_1line=summary)
        with self.engine.begin() as connection:
            # BEGIN IMMEDIATE serializes writers before the version/replay check (including other connections).
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            existing = connection.execute(select(turns).where(self._where(turns, profile_id, character_id),
                                          turns.c.client_turn_id == turn_id)).mappings().first()
            if existing:
                if existing["payload_hash"] != payload_hash:
                    raise conflict()
                return existing["response"]
            changed = connection.execute(update(relationships).where(
                self._where(relationships, profile_id, character_id), relationships.c.version == before.version
            ).values(**values, flags=flags, summary=summary, history=history[-12:],
                     recent=[item.model_dump() for item in (before.recent + [decision.interaction])[-3:]],
                     version=before.version + 1, turn_count=before.turn_count + 1))
            if changed.rowcount != 1:
                raise ChatError("STATE_CONFLICT", "대화 상태가 변경되었습니다. 다시 시도해 주세요.", retryable=True)
            self.failpoint("after_relationship")
            for candidate in accepted:
                subject = memory_subject(candidate["kind"], candidate["content"])
                if subject:
                    old = connection.execute(select(memories).where(
                        self._where(memories, profile_id, character_id))).mappings().all()
                    old_keys = [item["key"] for item in old if memory_subject(item["kind"], item["content"]) == subject]
                    if old_keys:
                        connection.execute(delete(memories).where(self._where(memories, profile_id, character_id),
                                                                  memories.c.key.in_(old_keys)))
                where = self._where(memories, profile_id, character_id) & (memories.c.key == candidate["key"])
                connection.execute(delete(memories).where(where))
                connection.execute(insert(memories).values(profile_id=profile_id, character_id=character_id,
                    **candidate, source_turn=turn_id, updated=time.time()))
            obsolete = connection.execute(select(memories.c.key).where(
                self._where(memories, profile_id, character_id)
            ).order_by(memories.c.importance.desc(), memories.c.updated.desc(), memories.c.key).offset(50)).scalars().all()
            if obsolete:
                connection.execute(delete(memories).where(self._where(memories, profile_id, character_id),
                                                          memories.c.key.in_(obsolete)))
            self.failpoint("after_memory")
            connection.execute(insert(turns).values(profile_id=profile_id, character_id=character_id,
                client_turn_id=turn_id, payload_hash=payload_hash, response=response,
                decision=decision.model_dump(), user_message=message, created=time.time()))
            self.failpoint("after_turn")
        self.failpoint("after_commit")
        emit("memory_committed", user_message=message, candidate_checks=memory_audit,
             stored=accepted, evicted_keys=obsolete,
             derived_profile_updates=profile_updates(message, before.history[-1]["content"] if before.history else ""),
             derived_events=dialogue_events(message, decision.reply, turn_id))
        return response

    def import_legacy(self, source_id, session_id, raw, character_id, defaults):
        values = from_legacy(raw.get("affection_total", 0), defaults)
        history = raw.get("history", [])
        if not isinstance(history, list) or any(
            not isinstance(item, dict) or item.get("role") not in ("user", "assistant")
            or not isinstance(item.get("content"), str) for item in history
        ):
            raise ValueError("Invalid legacy history")
        flags = raw.get("flags", [])
        if not isinstance(flags, list) or not all(isinstance(item, str) for item in flags):
            raise ValueError("Invalid legacy flags")
        summary = str(raw.get("memory_1line", ""))[:400]
        with self.engine.begin() as connection:
            connection.exec_driver_sql("BEGIN IMMEDIATE")
            existing = connection.execute(select(imports.c.profile_id).where(imports.c.source_id == source_id)).first()
            if existing:
                return existing[0], False
            if connection.execute(select(sessions.c.id).where(sessions.c.id == session_id)).first():
                raise ChatError("MIGRATION_CONFLICT", "이미 사용 중인 대화입니다.")
            profile_id = uuid.uuid4().hex
            connection.execute(insert(profiles).values(id=profile_id, created=time.time()))
            self._new_relationship(connection, profile_id, character_id, values, flags=flags, summary=summary,
                                   history=history[-12:], turn_count=len(history) // 2)
            connection.execute(insert(sessions).values(id=session_id, profile_id=profile_id, character_id=character_id))
            connection.execute(insert(imports).values(source_id=source_id, profile_id=profile_id, imported_at=time.time()))
            self.failpoint("after_import")
        return profile_id, True

    def delete_profile(self, profile_id):
        with self.engine.begin() as connection:
            connection.execute(delete(profiles).where(profiles.c.id == profile_id))

        forget(self.path, profile_id)

    def reset_profile(self, profile_id, character_id, defaults):
        # Rotate the identity: a delayed request cannot recreate or mutate reset state.
        new_profile, new_session = uuid.uuid4().hex, uuid.uuid4().hex
        with self.engine.begin() as connection:
            connection.execute(delete(profiles).where(profiles.c.id == profile_id))
            connection.execute(insert(profiles).values(id=new_profile, created=time.time()))
            self._new_relationship(connection, new_profile, character_id, defaults)
            connection.execute(insert(sessions).values(id=new_session, profile_id=new_profile, character_id=character_id))
        forget(self.path, profile_id)
        return new_session, new_profile

    def backup(self, destination):
        destination = Path(destination).resolve()
        if destination == self.path or destination.exists():
            raise ValueError("Backup destination must be a new file")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)) as source:
            with closing(sqlite3.connect(destination)) as target:
                source.backup(target)
                if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                    raise RuntimeError("Backup integrity check failed")
