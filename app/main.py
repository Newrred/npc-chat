from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.models import ChatRequest, ChatResponse
from app.services.comfy_service import ComfyService
from app.services.llm_service import LLMService

app = FastAPI(title="NPC Backend API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

llm_service = LLMService()
comfy_service = ComfyService()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    history_payload = [{"role": t.role, "content": t.content} for t in req.history]
    npc = llm_service.chat(req.message, history_payload)

    comfy = await comfy_service.maybe_generate(
        comfy_on=req.comfy_on,
        face=npc["face"],
        tags=npc["tags"],
        reply=npc["reply"],
    )

    return ChatResponse(
        **npc,
        comfy_status=comfy["comfy_status"],
        image_url=comfy["image_url"],
        image_prompt=comfy["image_prompt"],
    )
