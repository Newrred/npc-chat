from contextlib import asynccontextmanager
from dataclasses import dataclass, field
import json
import time
import uuid

from redis.asyncio import Redis

from app.config import settings


@dataclass
class SessionState:
    affection_total: int = 0
    flags: list[str] = field(default_factory=list)
    memory_1line: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    last_access_ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, object]:
        return {
            "affection_total": self.affection_total,
            "flags": list(self.flags),
            "memory_1line": self.memory_1line,
            "history": list(self.history),
            "last_access_ts": self.last_access_ts,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, object]) -> "SessionState":
        history = raw.get("history")
        flags = raw.get("flags")
        return cls(
            affection_total=int(raw.get("affection_total", 0)),
            flags=[str(flag).strip() for flag in (flags or []) if str(flag).strip()],
            memory_1line=str(raw.get("memory_1line", "") or ""),
            history=[item for item in (history or []) if isinstance(item, dict)],
            last_access_ts=float(raw.get("last_access_ts", time.time())),
        )


class RedisSessionStore:
    def __init__(self) -> None:
        self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
        self._prefix = (settings.redis_key_prefix or "npc").strip() or "npc"
        self._session_ttl_sec = max(1, settings.session_ttl_sec)
        self._lock_timeout_sec = max(1, settings.redis_lock_timeout_sec)
        self._lock_blocking_timeout_sec = max(1, settings.redis_lock_blocking_timeout_sec)

    async def ping(self) -> None:
        await self._redis.ping()

    async def close(self) -> None:
        await self._redis.aclose()

    def _session_key(self, session_id: str) -> str:
        return f"{self._prefix}:session:{session_id}"

    def _lock_key(self, session_id: str) -> str:
        return f"{self._prefix}:session-lock:{session_id}"

    async def get(self, session_id: str) -> SessionState | None:
        raw = await self._redis.get(self._session_key(session_id))
        if not raw:
            return None

        state = SessionState.from_dict(json.loads(raw))
        await self.touch(session_id, state)
        return state

    async def create(self) -> tuple[str, SessionState]:
        session_id = uuid.uuid4().hex
        state = SessionState()
        await self.save(session_id, state)
        return session_id, state

    async def get_or_create(self, session_id: str | None) -> tuple[str, SessionState]:
        sid = (session_id or "").strip()
        if sid:
            state = await self.get(sid)
            if state is not None:
                return sid, state
        return await self.create()

    async def save(self, session_id: str, state: SessionState) -> None:
        state.last_access_ts = time.time()
        # Store ASCII-safe JSON so Redis viewers / Windows terminals don't
        # replace Korean text with '?' while keeping round-trip decoding safe.
        payload = json.dumps(state.to_dict(), ensure_ascii=True)
        await self._redis.set(self._session_key(session_id), payload, ex=self._session_ttl_sec)

    async def touch(self, session_id: str, state: SessionState | None = None) -> None:
        if state is not None:
            await self.save(session_id, state)
            return
        await self._redis.expire(self._session_key(session_id), self._session_ttl_sec)

    @asynccontextmanager
    async def session_lock(self, session_id: str):
        lock = self._redis.lock(
            self._lock_key(session_id),
            timeout=self._lock_timeout_sec,
            blocking_timeout=self._lock_blocking_timeout_sec,
        )
        acquired = await lock.acquire()
        if not acquired:
            raise TimeoutError(f"Could not acquire Redis session lock for {session_id}")
        try:
            yield
        finally:
            try:
                await lock.release()
            except Exception:
                pass
