from dataclasses import dataclass, field
import os

from dotenv import load_dotenv

load_dotenv()


def _parse_cors_origins(raw: str) -> list[str]:
    items = [x.strip() for x in (raw or "").split(",") if x.strip()]
    return items or ["*"]


@dataclass
class Settings:
    # vLLM/OpenAI-compatible endpoint
    llm_base_url: str = os.getenv("NPC_BASE_URL", "http://localhost:8000/v1")
    llm_api_key: str = os.getenv("NPC_API_KEY", "my-local-key")
    llm_model: str = os.getenv("NPC_MODEL", "Qwen/Qwen3-8B-AWQ")
    llm_timeout_sec: float = float(os.getenv("NPC_TIMEOUT", "120"))
    llm_temperature: float = float(os.getenv("NPC_TEMP", "0.4"))
    llm_top_p: float = float(os.getenv("NPC_TOP_P", "1.0"))
    llm_top_k: int = int(os.getenv("NPC_TOP_K", "20"))
    llm_max_tokens: int = int(os.getenv("NPC_MAX_TOKENS", "1024"))

    # Browser access control
    cors_origins: list[str] = field(default_factory=lambda: _parse_cors_origins(os.getenv("CORS_ORIGINS", "*")))

    # ComfyUI switch
    comfy_enabled: bool = os.getenv("COMFY_ENABLED", "false").lower() == "true"
    comfy_connect: bool = os.getenv("COMFY_CONNECT", "false").lower() == "true"
    comfy_base_url: str = os.getenv("COMFY_BASE_URL", "https://example-comfy.trycloudflare.com")
    comfy_timeout_sec: float = float(os.getenv("COMFY_TIMEOUT", "120"))


settings = Settings()
