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
    character_id: str = os.getenv("NPC_CHARACTER_ID", "default")
    llm_backend: str = os.getenv("NPC_LLM_BACKEND", "vllm")
    llm_base_url: str = os.getenv("NPC_BASE_URL", "http://localhost:8000/v1")
    llm_api_key: str = os.getenv("NPC_API_KEY", "my-local-key")
    llm_model: str = os.getenv("NPC_MODEL", "Qwen/Qwen3-8B-AWQ")
    llm_timeout_sec: float = float(os.getenv("NPC_TIMEOUT", "120"))
    llm_temperature: float = float(os.getenv("NPC_TEMP", "0.4"))
    llm_top_p: float = float(os.getenv("NPC_TOP_P", "1.0"))
    llm_top_k: int = int(os.getenv("NPC_TOP_K", "20"))
    llm_presence_penalty: float = float(os.getenv("NPC_PRESENCE_PENALTY", "0.5"))
    llm_frequency_penalty: float = float(os.getenv("NPC_FREQUENCY_PENALTY", "0.3"))
    llm_repetition_penalty: float = float(os.getenv("NPC_REPETITION_PENALTY", "1.08"))
    llm_max_tokens: int = int(os.getenv("NPC_MAX_TOKENS", "1024"))

    # Browser access control
    cors_origins: list[str] = field(default_factory=lambda: _parse_cors_origins(os.getenv("CORS_ORIGINS", "*")))
    session_ttl_sec: int = int(os.getenv("SESSION_TTL_SEC", "3600"))
    redis_url: str = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    redis_key_prefix: str = os.getenv("REDIS_KEY_PREFIX", "npc")
    redis_lock_timeout_sec: int = int(os.getenv("REDIS_LOCK_TIMEOUT_SEC", "30"))
    redis_lock_blocking_timeout_sec: int = int(os.getenv("REDIS_LOCK_BLOCKING_TIMEOUT_SEC", "10"))

    # ComfyUI switch
    comfy_enabled: bool = os.getenv("COMFY_ENABLED", "false").lower() == "true"
    comfy_connect: bool = os.getenv("COMFY_CONNECT", "false").lower() == "true"
    comfy_base_url: str = os.getenv("COMFY_BASE_URL", "https://example-comfy.trycloudflare.com")
    comfy_timeout_sec: float = float(os.getenv("COMFY_TIMEOUT", "120"))
    comfy_character_id: str = os.getenv("COMFY_CHARACTER_ID", "npc-default")
    comfy_style_version: str = os.getenv("COMFY_STYLE_VERSION", "v1")
    comfy_gen_cooldown_turns: int = int(os.getenv("COMFY_GEN_COOLDOWN_TURNS", "10"))
    comfy_gen_max_per_minute: int = int(os.getenv("COMFY_GEN_MAX_PER_MINUTE", "3"))
    comfy_gen_max_inflight_per_session: int = int(os.getenv("COMFY_GEN_MAX_INFLIGHT_PER_SESSION", "1"))
    comfy_gen_backoff_sec: int = int(os.getenv("COMFY_GEN_BACKOFF_SEC", "30"))
    comfy_force_regen_faces: str = os.getenv("COMFY_FORCE_REGEN_FACES", "angry,crying,scared,excited")
    comfy_cache_ttl_sec: int = int(os.getenv("COMFY_CACHE_TTL_SEC", "1800"))


settings = Settings()
