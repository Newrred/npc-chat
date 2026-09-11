from app.debug_trace import capture, emit
from copy import copy
from contextlib import asynccontextmanager
from functools import partial
import uuid
import logging
import sqlite3

from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from fastapi import APIRouter, FastAPI, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.models import CharacterId, ChatRequest, ChatResponse, FaceType, ImageStatusResponse
from app.services.comfy_service import ComfyService
from app.services.health_service import check_dependencies, check_llm
from app.services.decision_service import LLMOutputError, LLMTransportError
from app.services.llm_service_factory import create_llm_service
from app.repository import SQLiteRepository, payload_digest
from app.relationship import calculate, stage
from app.character_config import load_character_config
from app.coordinator import TurnCoordinator
from app.decision import LLMDecision
from app.errors import ChatError
from app.web import mount_frontend
from app.remote_access import AccessVerifier, RemoteBoundary, RemoteConfig
from app.guest_access import GuestLimits


router = APIRouter()


@router.get("/api/health")
@router.get("/api/live")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/ready")
async def ready(request: Request) -> JSONResponse:
    state = request.app.state
    dependencies = await check_dependencies(
        {"database": state.repository.ping, "llm": state.llm_probe},
        timeout_sec=settings.health_timeout_sec,
    )
    is_ready = all(status == "ok" for status in dependencies.values())
    return JSONResponse(
        status_code=200 if is_ready else 503,
        content={"status": "ready" if is_ready else "not_ready", "dependencies": dependencies},
    )


class SessionRequest(BaseModel):
    session_id: str | None = Field(default=None, max_length=128)
    profile_id: str | None = Field(default=None, max_length=128)
    character_id: CharacterId | None = None


class ResetRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    profile_id: str = Field(min_length=1, max_length=128)
    character_id: CharacterId | None = None


def requested_character(character_id: str | None):
    try:
        return load_character_config(character_id or settings.character_id)
    except FileNotFoundError:
        raise ChatError("CHARACTER_NOT_FOUND", "선택한 캐릭터를 찾을 수 없습니다.", 404)


def service_for_character(service, character):
    if not hasattr(service, "character") or character.character_id == settings.character_id:
        return service
    selected = copy(service)
    selected.character = character
    return selected


async def conversation_identity(request, session_id, profile_id, character):
    state = request.app.state
    owner = getattr(request.state, "remote_owner", None)
    if owner:
        return await run_in_threadpool(state.repository.resolve_owned, owner, session_id, profile_id,
                                       character.character_id, character.initial_relationship)
    return await run_in_threadpool(state.repository.resolve, session_id, profile_id,
                                   character.character_id, character.initial_relationship)


@router.get("/api/conversation")
async def conversation(request: Request, session_id: str = Query(min_length=1, max_length=128),
                       profile_id: str = Query(min_length=1, max_length=128),
                       character_id: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$"),
                       before: str | None = Query(default=None, max_length=128),
                       limit: int = Query(default=50, ge=1, le=100)):
    character = requested_character(character_id)
    _, profile = await conversation_identity(request, session_id, profile_id, character)
    page = await run_in_threadpool(request.app.state.repository.history_page,
                                  profile, character.character_id, before, limit)
    return JSONResponse(page, headers={"Cache-Control": "no-store"})


@router.post("/api/conversation/reset")
async def reset_conversation(req: ResetRequest, request: Request):
    character = requested_character(req.character_id)
    async def execute(cancelled):
        session, profile = await conversation_identity(request, req.session_id, req.profile_id, character)
        if cancelled():
            raise ChatError("TURN_CANCELLED", "취소된 요청입니다.", 499)
        return await run_in_threadpool(request.app.state.repository.reset_conversation,
            session, profile, character.character_id, character.initial_relationship)
    return await request.app.state.coordinator.submit(execute)


@router.post("/api/session")
async def open_session(req: SessionRequest, request: Request):
    state = request.app.state
    character = requested_character(req.character_id)
    if getattr(request.state, "remote_owner", None):
        if state.guest_limits:
            await run_in_threadpool(state.guest_limits.admit, request.state.remote_owner)
        session_id, profile_id = await run_in_threadpool(partial(
            state.repository.resolve_owned, request.state.remote_owner, req.session_id, req.profile_id,
            character.character_id, character.initial_relationship, create=True))
        return {"session_id": session_id, "profile_id": profile_id}
    session_id, profile_id = await run_in_threadpool(
        partial(state.repository.resolve, req.session_id, req.profile_id, character.character_id,
                character.initial_relationship, allow_stale=True))
    return {"session_id": session_id, "profile_id": profile_id}


@router.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, request: Request):
    app_state = request.app.state
    character = requested_character(req.character_id)
    if req.client_turn_id and not (req.session_id or req.profile_id):
        raise ChatError("SESSION_REQUIRED", "먼저 대화 세션을 생성해 주세요.", 422)
    if getattr(request.state, "remote_owner", None):
        if not req.client_turn_id:
            raise ChatError("TURN_ID_REQUIRED", "요청 식별자가 필요합니다.", 422)
        session_id, profile_id = await run_in_threadpool(
            app_state.repository.resolve_owned, request.state.remote_owner, req.session_id, req.profile_id,
            character.character_id, character.initial_relationship)
    else:
        session_id, profile_id = await run_in_threadpool(
            app_state.repository.resolve, req.session_id, req.profile_id, character.character_id,
            character.initial_relationship)
    turn_id = req.client_turn_id or uuid.uuid4().hex  # Legacy clients remain one-shot only.
    digest = payload_digest(req.message, req.comfy_on)
    service = service_for_character(app_state.llm_service, character)
    draft = None
    token = request.headers.get("X-NPC-Local-Prompt")
    if token:
        from app.inspector_prompt import verify, character_with_draft, revision
        try:
            draft = verify(app_state.repository.path, token, req.model_dump())
        except ValueError:
            raise ChatError("INVALID_PROMPT_EXPERIMENT", "유효하지 않은 로컬 실험 요청입니다.", 403)
        if settings.llm_generation_mode != "two_stage" or not hasattr(service, "character"):
            raise ChatError("PROMPT_EXPERIMENT_UNAVAILABLE", "프롬프트 실험은 두 단계 생성 모드에서 지원합니다.", 409)
        service = copy(service)
        service.prompt_experiment = True
        service.character = character_with_draft(character, draft)
        digest = payload_digest(req.message + "\nlocal-prompt:" + draft.model_dump_json(), req.comfy_on)

    async def execute_turn(cancelled):
        repository = app_state.repository
        # Revoke queued requests from tabs whose room was closed before execution.
        await conversation_identity(request, session_id, profile_id, character)
        cached = await run_in_threadpool(repository.replay, profile_id, character.character_id, turn_id, digest)
        if cached is not None:
            emit("replay", response=cached)
            return cached
        if app_state.guest_limits:
            await run_in_threadpool(partial(app_state.guest_limits.admit, request.state.remote_owner, charge=True))
        before = await run_in_threadpool(repository.load, profile_id, character.character_id)
        notes = await run_in_threadpool(repository.recall, profile_id, character.character_id, req.message, before.history)
        emit("context_selected", selected_memories=[dict(note) for note in notes], history_messages=len(before.history),
             summary=before.summary, relationship=before.values.model_dump())
        generated = await run_in_threadpool(partial(
            service.decide, message=req.message, history=before.history,
            memory_1line=before.summary, flags=before.flags,
            relationship={"values": before.values.model_dump(), "stage": stage(before.values)},
            memories=[{"content": note["content"], "kind": note["kind"]} for note in notes],
        ))
        decision = LLMDecision.model_validate(generated.decision.model_dump())
        decision.flags_set = [flag for flag in decision.flags_set if flag in character.allowed_flags]
        result = calculate(before.values, decision.interaction, before.recent, character.relationship_matrix)
        if cancelled():
            raise ChatError("TURN_CANCELLED", "취소된 요청입니다.", 499, True)
        comfy = await app_state.comfy_service.maybe_generate(
            comfy_on=req.comfy_on, session_id=session_id, turn_index=before.turn_count + 1,
            face=decision.face, tags=decision.emotion_tags, reply=decision.reply)
        flags = sorted(set(before.flags) | set(decision.flags_set))
        response = ChatResponse(
            session_id=session_id, profile_id=profile_id, turn_id=turn_id,
            reply=decision.reply, face=decision.face, internal_emotion=decision.internal_emotion,
            affection_delta=result.delta.affection, affection_total=result.values.affection,
            relationship=result, expression={"face": decision.face, "internal_emotion": decision.internal_emotion,
                                              "tags": decision.emotion_tags},
            tags=decision.emotion_tags, flags_set=decision.flags_set, flags=flags, memory_1line=before.summary,
            memory={"summary_updated": False, "accepted_candidates": 0,
                    "grounded_recall": getattr(generated, "grounded_recall", False)},
            image={"status": comfy["comfy_status"], "source": comfy.get("image_source", "none"),
                   "url": comfy.get("image_url")},
            comfy_status=comfy["comfy_status"], image_url=comfy.get("image_url"),
            image_prompt=comfy.get("image_prompt"), image_source=comfy.get("image_source", "none"),
        ).model_dump()
        if cancelled():
            raise ChatError("TURN_CANCELLED", "취소된 요청입니다.", 499, True)
        return await run_in_threadpool(partial(
            repository.commit, profile_id=profile_id, character_id=character.character_id, turn_id=turn_id,
            payload_hash=digest, before=before, decision=decision, result=result, message=req.message,
            response=response, flags=flags))

    async def execute(cancelled):
        with capture(repository_database, settings.debug_trace, profile_id, character.character_id, turn_id):
            if draft is not None:
                emit("prompt_experiment", revision=revision(draft), draft=draft.model_dump())
            result = await execute_turn(cancelled)
            emit("completed", response=result)
            return result

    repository_database = app_state.repository.path
    return await app_state.coordinator.submit(execute)


@router.get("/api/image/status", response_model=ImageStatusResponse)
async def image_status(request: Request, session_id: str, face: FaceType,
                       character_id: str | None = Query(default=None, pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")) -> ImageStatusResponse:
    character = requested_character(character_id)
    if getattr(request.state, "remote_owner", None):
        await run_in_threadpool(request.app.state.repository.resolve_owned, request.state.remote_owner,
                                session_id, None, character.character_id,
                                character.initial_relationship)
    comfy_service = request.app.state.comfy_service
    status = await comfy_service.get_face_image_status(session_id=session_id, face=face)
    return ImageStatusResponse(
        session_id=session_id,
        face=face,
        comfy_status=status["comfy_status"],
        image_url=status.get("image_url"),
        image_source=status.get("image_source", "none"),
    )


def create_app(*, llm_service=None, session_store=None, repository=None, comfy_service=None, llm_probe=None,
               remote_config=None, access_verifier=None) -> FastAPI:
    """Inject dependencies for offline tests without adding a public fake mode."""

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        store = application.state.repository
        if hasattr(store, "lease"):
            await run_in_threadpool(store.lease.acquire)
        try:
            try:
                if hasattr(store, "upgrade"):
                    await run_in_threadpool(store.upgrade)
            except (SQLAlchemyError, OSError):
                logging.getLogger(__name__).warning("database_startup_unavailable")
            yield
        finally:
            await application.state.coordinator.close()
            await store.close()
            if llm_service is None:
                await run_in_threadpool(application.state.llm_service.client.close)

    remote_config = remote_config or RemoteConfig.from_env()
    remote_config.validate()
    remote = remote_config.mode != "local"
    application = FastAPI(title="NPC Backend API", version="0.5.0", lifespan=lifespan,
                          docs_url=None if remote else "/docs", redoc_url=None if remote else "/redoc",
                          openapi_url=None if remote else "/openapi.json")
    @application.exception_handler(LLMOutputError)
    async def invalid_output(_request, _exc):
        return JSONResponse(status_code=502, content={"error": {
            "code": "LLM_INVALID_OUTPUT", "message": "모델 응답 형식을 확인하지 못했습니다.", "retryable": True,
        }})

    @application.exception_handler(LLMTransportError)
    async def unavailable_llm(_request, _exc):
        return JSONResponse(status_code=503, content={"error": {
            "code": "LLM_UNAVAILABLE", "message": "대화 모델에 연결할 수 없습니다.", "retryable": True,
        }})

    @application.exception_handler(ChatError)
    async def chat_error(_request, exc):
        return JSONResponse(status_code=exc.status, content={"error": {
            "code": exc.code, "message": exc.message, "retryable": exc.retryable,
        }})

    @application.exception_handler(sqlite3.Error)
    @application.exception_handler(SQLAlchemyError)
    async def persistence_error(_request, _exc):
        return JSONResponse(status_code=503, content={"error": {
            "code": "PERSISTENCE_FAILURE", "message": "대화 상태를 저장하거나 읽을 수 없습니다.", "retryable": True,
        }})

    application.state.llm_service = create_llm_service() if llm_service is None else llm_service
    application.state.repository = repository or session_store or SQLiteRepository(settings.database_path)
    application.state.guest_limits = (GuestLimits(str(application.state.repository.path) + ".usage.sqlite3",
                                                 remote_config) if remote_config.mode == "guest" else None)
    application.state.session_store = application.state.repository  # Compatibility test seam.
    application.state.character = load_character_config()
    application.state.coordinator = TurnCoordinator(settings.queue_capacity, settings.queue_wait_sec)
    application.state.comfy_service = ComfyService() if comfy_service is None else comfy_service
    application.state.llm_probe = check_llm if llm_probe is None else llm_probe
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[remote_config.origin] if remote else settings.cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    if remote:
        application.add_middleware(RemoteBoundary, config=remote_config,
                                   verifier=(access_verifier or AccessVerifier(remote_config))
                                   if remote_config.mode == "cloudflare" else None)
    application.include_router(router)
    mount_frontend(application)
    return application


app = create_app()
