from typing import Protocol

from app.config import settings
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
    backend = settings.llm_backend.strip().lower()
    if backend == "llama_cpp":
        return LlamaCppLLMService()
    return LLMService()
