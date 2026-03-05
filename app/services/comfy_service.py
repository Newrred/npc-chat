import asyncio
from collections import deque
from dataclasses import dataclass, field
import time
from typing import Any

import httpx

from app.config import settings


def build_face_prompt(face: str, tags: list[str], reply: str) -> str:
    tags_part = ", ".join(tags[:2]) if tags else "neutral"
    return f"anime portrait, npc face, expression: {face}, mood tags: {tags_part}, dialogue mood: {reply[:80]}"


@dataclass
class SessionImagePolicyState:
    recent_generation_timestamps: deque[float] = field(default_factory=deque)
    inflight_count: int = 0
    last_face: str | None = None
    last_generation_turn_by_face: dict[str, int] = field(default_factory=dict)


class ComfyService:
    def __init__(self) -> None:
        self._generated_cache: dict[str, str] = {}
        self._job_status_by_key: dict[str, str] = {}
        self._retry_after_by_key: dict[str, float] = {}
        self._session_state_by_id: dict[str, SessionImagePolicyState] = {}
        self._bg_tasks: set[asyncio.Task[Any]] = set()
        self._lock = asyncio.Lock()
        self._force_regen_faces = {
            face.strip() for face in settings.comfy_force_regen_faces.split(",") if face.strip()
        }

    @staticmethod
    def _safe_task_discard(tasks: set[asyncio.Task[Any]], task: asyncio.Task[Any]) -> None:
        tasks.discard(task)

    @staticmethod
    def _prune_old_timestamps(bucket: deque[float], *, now_ts: float, window_sec: float = 60.0) -> None:
        while bucket and (now_ts - bucket[0]) > window_sec:
            bucket.popleft()

    def _cache_key(self, face: str) -> str:
        return f"{settings.comfy_character_id}:{settings.comfy_style_version}:{face}"

    @staticmethod
    def _base_face_url(face: str) -> str | None:
        tmpl = (settings.comfy_face_url_template or "").strip()
        if not tmpl:
            return None
        face_slug = face.strip().lower().replace(" ", "_")
        return tmpl.format(face=face, face_slug=face_slug)

    async def _decrease_inflight(self, session_id: str) -> None:
        async with self._lock:
            state = self._session_state_by_id.setdefault(session_id, SessionImagePolicyState())
            state.inflight_count = max(0, state.inflight_count - 1)

    async def _run_generation_job(
        self,
        *,
        cache_key: str,
        session_id: str,
        prompt: str,
        face: str,
        tags: list[str],
    ) -> None:
        async with self._lock:
            self._job_status_by_key[cache_key] = "generating"

        payload = {
            "prompt": prompt,
            "meta": {
                "source": "npc-web",
                "character_id": settings.comfy_character_id,
                "style_version": settings.comfy_style_version,
                "face": face,
                "tags": tags[:2],
            },
        }

        try:
            async with httpx.AsyncClient(timeout=settings.comfy_timeout_sec) as client:
                resp = await client.post(f"{settings.comfy_base_url}/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()

            image_url = data.get("image_url")
            if not image_url:
                raise ValueError("missing image_url from comfy response")

            async with self._lock:
                self._generated_cache[cache_key] = image_url
                self._job_status_by_key[cache_key] = "generated"
                self._retry_after_by_key.pop(cache_key, None)
        except Exception:
            async with self._lock:
                self._job_status_by_key[cache_key] = "error"
                self._retry_after_by_key[cache_key] = time.time() + max(0, settings.comfy_gen_backoff_sec)
        finally:
            await self._decrease_inflight(session_id)

    async def _maybe_enqueue_generation(
        self,
        *,
        session_id: str,
        turn_index: int,
        cache_key: str,
        face: str,
        tags: list[str],
        prompt: str,
    ) -> tuple[bool, str]:
        now_ts = time.time()

        async with self._lock:
            state = self._session_state_by_id.setdefault(session_id, SessionImagePolicyState())
            face_changed = state.last_face is None or state.last_face != face
            state.last_face = face

            if not face_changed and face not in self._force_regen_faces:
                return False, "same_face_no_force"

            self._prune_old_timestamps(state.recent_generation_timestamps, now_ts=now_ts)
            if state.inflight_count >= max(1, settings.comfy_gen_max_inflight_per_session):
                return False, "inflight_limit"
            if len(state.recent_generation_timestamps) >= max(1, settings.comfy_gen_max_per_minute):
                return False, "rate_limited"

            last_turn = state.last_generation_turn_by_face.get(face, -10_000)
            if (turn_index - last_turn) < max(0, settings.comfy_gen_cooldown_turns):
                return False, "cooldown"

            job_status = self._job_status_by_key.get(cache_key)
            if job_status in {"queued", "generating"}:
                return False, "already_in_progress"

            retry_after = self._retry_after_by_key.get(cache_key, 0.0)
            if now_ts < retry_after:
                return False, "backoff"

            state.inflight_count += 1
            state.recent_generation_timestamps.append(now_ts)
            state.last_generation_turn_by_face[face] = turn_index
            self._job_status_by_key[cache_key] = "queued"

        task = asyncio.create_task(
            self._run_generation_job(
                cache_key=cache_key,
                session_id=session_id,
                prompt=prompt,
                face=face,
                tags=tags,
            )
        )
        self._bg_tasks.add(task)
        task.add_done_callback(lambda t: self._safe_task_discard(self._bg_tasks, t))
        return True, "queued"

    async def get_face_image_status(
        self,
        *,
        session_id: str,
        face: str,
    ) -> dict[str, Any]:
        _ = session_id
        base_url = self._base_face_url(face)
        cache_key = self._cache_key(face)

        async with self._lock:
            generated_url = self._generated_cache.get(cache_key)
            job_status = self._job_status_by_key.get(cache_key)

        if generated_url:
            return {
                "comfy_status": "generated",
                "image_url": generated_url,
                "image_source": "generated",
            }
        if job_status in {"queued", "generating"}:
            return {
                "comfy_status": "queued",
                "image_url": base_url,
                "image_source": "base" if base_url else "none",
            }
        if job_status == "error":
            return {
                "comfy_status": "error",
                "image_url": base_url,
                "image_source": "base" if base_url else "none",
            }
        if not settings.comfy_enabled:
            return {
                "comfy_status": "disabled",
                "image_url": base_url,
                "image_source": "base" if base_url else "none",
            }
        if not settings.comfy_connect:
            return {
                "comfy_status": "stubbed",
                "image_url": base_url,
                "image_source": "base" if base_url else "none",
            }
        return {
            "comfy_status": "base",
            "image_url": base_url,
            "image_source": "base" if base_url else "none",
        }

    async def maybe_generate(
        self,
        *,
        comfy_on: bool,
        session_id: str,
        turn_index: int,
        face: str,
        tags: list[str],
        reply: str,
    ) -> dict[str, Any]:
        prompt = build_face_prompt(face, tags, reply)
        base_url = self._base_face_url(face)
        cache_key = self._cache_key(face)

        async with self._lock:
            generated_url = self._generated_cache.get(cache_key)

        if not comfy_on or not settings.comfy_enabled:
            return {
                "comfy_status": "disabled",
                "image_url": base_url,
                "image_prompt": prompt,
                "image_source": "base" if base_url else "none",
            }

        # Toggle is on but remote connection is intentionally disabled.
        if not settings.comfy_connect:
            return {
                "comfy_status": "stubbed",
                "image_url": generated_url or base_url,
                "image_prompt": prompt,
                "image_source": "generated" if generated_url else ("base" if base_url else "none"),
            }

        if generated_url:
            return {
                "comfy_status": "generated",
                "image_url": generated_url,
                "image_prompt": prompt,
                "image_source": "generated",
            }

        enqueued, _reason = await self._maybe_enqueue_generation(
            session_id=session_id,
            turn_index=turn_index,
            cache_key=cache_key,
            face=face,
            tags=tags,
            prompt=prompt,
        )
        if enqueued:
            return {
                "comfy_status": "queued",
                "image_url": base_url,
                "image_prompt": prompt,
                "image_source": "base" if base_url else "none",
            }

        status = await self.get_face_image_status(session_id=session_id, face=face)
        status["image_prompt"] = prompt
        return status
