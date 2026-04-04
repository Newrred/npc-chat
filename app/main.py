import asyncio
from dataclasses import dataclass, field
from functools import partial
from pathlib import Path
import time
import uuid

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.models import ChatRequest, ChatResponse, FaceType, ImageStatusResponse
from app.services.comfy_service import ComfyService
from app.services.llm_service import LLMService


@dataclass
class SessionState:
    affection_total: int = 0
    flags: set[str] = field(default_factory=set)
    memory_1line: str = ""
    history: list[dict[str, str]] = field(default_factory=list)
    last_access_ts: float = field(default_factory=time.time)


app = FastAPI(title="NPC Backend API", version="0.3.0")
PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_STATIC_DIR = PROJECT_ROOT / "app" / "static"
FRONTEND_FACES_DIR = PROJECT_ROOT / "frontend" / "faces"

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = LLMService()
comfy_service = ComfyService()
session_store: dict[str, SessionState] = {}
session_locks: dict[str, asyncio.Lock] = {}

if FRONTEND_FACES_DIR.is_dir():
    app.mount("/static/faces", StaticFiles(directory=str(FRONTEND_FACES_DIR)), name="static-faces")
if APP_STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(APP_STATIC_DIR)), name="static")


def _cleanup_stale_sessions(now_ts: float) -> None:
    ttl_sec = max(1, settings.session_ttl_sec)
    for sid, state in list(session_store.items()):
        if (now_ts - state.last_access_ts) <= ttl_sec:
            continue
        lock = session_locks.get(sid)
        if lock and lock.locked():
            continue
        session_store.pop(sid, None)
        session_locks.pop(sid, None)


def _get_session_lock(session_id: str) -> asyncio.Lock:
    return session_locks.setdefault(session_id, asyncio.Lock())


def _get_or_create_session(session_id: str | None) -> tuple[str, SessionState]:
    now_ts = time.time()
    _cleanup_stale_sessions(now_ts)

    sid = (session_id or "").strip()
    if sid and sid in session_store:
        session_store[sid].last_access_ts = now_ts
        return sid, session_store[sid]

    sid = uuid.uuid4().hex
    state = SessionState(last_access_ts=now_ts)
    session_store[sid] = state
    return sid, state


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id, _ = _get_or_create_session(req.session_id)

    async with _get_session_lock(session_id):
        session_id, state = _get_or_create_session(session_id)

        # First request can bootstrap from client history if session is empty.
        if not state.history and req.history:
            state.history = [{"role": t.role, "content": t.content} for t in req.history]

        npc = await run_in_threadpool(
            partial(
                llm_service.chat,
                message=req.message,
                history=state.history,
                affection_total=state.affection_total,
                flags=sorted(state.flags),
                memory_1line=state.memory_1line,
            )
        )

        delta = int(npc.get("affection_delta", 0))
        delta = max(-10, min(10, delta))
        state.affection_total += delta
        state.flags.update(npc.get("flags_set") or [])
        state.memory_1line = npc.get("memory_1line") or state.memory_1line

        reply = npc.get("reply") or ""
        turn_index = (len(state.history) // 2) + 1
        state.history.extend(
            [
                {"role": "user", "content": req.message},
                {"role": "assistant", "content": reply},
            ]
        )
        if len(state.history) > 20:
            state.history = state.history[-20:]
        state.last_access_ts = time.time()

        comfy = await comfy_service.maybe_generate(
            comfy_on=req.comfy_on,
            session_id=session_id,
            turn_index=turn_index,
            face=npc["face"],
            tags=npc["tags"],
            reply=reply,
        )
        state.last_access_ts = time.time()

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            face=npc["face"],
            internal_emotion=npc.get("internal_emotion", "neutral"),
            affection_delta=delta,
            affection_total=state.affection_total,
            tags=npc["tags"],
            flags_set=npc.get("flags_set") or [],
            flags=sorted(state.flags),
            memory_1line=state.memory_1line,
            comfy_status=comfy["comfy_status"],
            image_url=comfy["image_url"],
            image_prompt=comfy["image_prompt"],
            image_source=comfy.get("image_source", "none"),
        )


@app.get("/api/image/status", response_model=ImageStatusResponse)
async def image_status(session_id: str, face: FaceType) -> ImageStatusResponse:
    status = await comfy_service.get_face_image_status(session_id=session_id, face=face)
    return ImageStatusResponse(
        session_id=session_id,
        face=face,
        comfy_status=status["comfy_status"],
        image_url=status.get("image_url"),
        image_source=status.get("image_source", "none"),
    )
