from functools import partial
import time

from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse, FaceType, ImageStatusResponse
from app.services.comfy_service import ComfyService
from app.services.llm_service_factory import create_llm_service
from app.session_store import RedisSessionStore


app = FastAPI(title="NPC Backend API", version="0.4.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = create_llm_service()
comfy_service = ComfyService()
session_store = RedisSessionStore()


@app.on_event("startup")
async def startup() -> None:
    await session_store.ping()


@app.on_event("shutdown")
async def shutdown() -> None:
    await session_store.close()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    session_id, _ = await session_store.get_or_create(req.session_id)

    async with session_store.session_lock(session_id):
        session_id, state = await session_store.get_or_create(session_id)

        if not state.history and req.history:
            state.history = [{"role": turn.role, "content": turn.content} for turn in req.history]

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

        flags = set(state.flags)
        flags.update(npc.get("flags_set") or [])
        state.flags = sorted(flags)
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
        await session_store.save(session_id, state)

        return ChatResponse(
            session_id=session_id,
            reply=reply,
            face=npc["face"],
            internal_emotion=npc.get("internal_emotion", "neutral"),
            affection_delta=delta,
            affection_total=state.affection_total,
            tags=npc["tags"],
            flags_set=npc.get("flags_set") or [],
            flags=state.flags,
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
