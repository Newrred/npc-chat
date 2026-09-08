from typing import Protocol

from app.config import settings
from app.services.decision_service import DecisionService
from app.services.llama_cpp_service import LlamaCppLLMService
from app.services.llm_service import LLMService


class ChatLLMService(Protocol):
    def chat(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        affection_total: int,
        flags: list[str],
        memory_1line: str,
    ) -> dict[str, object]: ...


def create_llm_service() -> ChatLLMService:
    if settings.llm_output_contract == "canonical":
        return DecisionService()
    if settings.llm_output_contract != "legacy":
        raise ValueError("NPC_OUTPUT_CONTRACT must be canonical or legacy")
    backend = settings.llm_backend.strip().lower()
    if backend == "llama_cpp":
        return LlamaCppLLMService()
    return LLMService()
