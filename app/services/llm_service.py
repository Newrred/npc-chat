import json
from typing import Any

from openai import OpenAI

from app.config import settings

FACE_ENUM = [
    "neutral", "happy", "sad", "angry", "crying", "smiling", "smirk", "shy smile",
    "blushing", "teary", "surprised", "confused", "annoyed", "pouting", "tired", "scared", "excited"
]

SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reply", "face", "affection_delta", "tags", "flags_set", "memory_1line"],
    "properties": {
        "reply": {"type": "string"},
        "face": {"type": "string", "enum": FACE_ENUM},
        "affection_delta": {"type": "integer", "minimum": -10, "maximum": 10},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "flags_set": {"type": "array", "items": {"type": "string"}},
        "memory_1line": {"type": "string", "minLength": 1, "maxLength": 60},
    },
}

SYSTEM_PROMPT = (
    "You are an NPC in a visual novel. "
    "Always answer with one JSON object only with keys: "
    "reply, face, affection_delta, tags, flags_set, memory_1line."
)


class LLMService:
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_sec,
            max_retries=0,
        )

    @staticmethod
    def _extract_json_object(raw: str) -> str:
        text = (raw or "").strip()
        left = text.find("{")
        right = text.rfind("}")
        if left == -1 or right <= left:
            raise ValueError("No JSON object found in model output")
        return text[left:right + 1]

    @staticmethod
    def _normalize(payload: dict[str, Any]) -> dict[str, Any]:
        reply = str(payload.get("reply", "")).strip()
        if not reply:
            raise ValueError("reply is empty")

        face = str(payload.get("face", "neutral")).strip()
        if face not in FACE_ENUM:
            face = "neutral"

        try:
            affection_delta = int(payload.get("affection_delta", 0))
        except Exception:
            affection_delta = 0
        affection_delta = max(-10, min(10, affection_delta))

        tags = payload.get("tags", [])
        if not isinstance(tags, list):
            tags = []
        tags = [str(x).strip() for x in tags if str(x).strip()]
        tags = list(dict.fromkeys(tags))[:2]
        if not tags:
            tags = ["neutral"]

        flags_set = payload.get("flags_set", [])
        if not isinstance(flags_set, list):
            flags_set = []
        flags_set = [str(x).strip() for x in flags_set if str(x).strip()]

        memory_1line = str(payload.get("memory_1line", "interaction happened")).strip()[:60]
        if not memory_1line:
            memory_1line = "interaction happened"

        return {
            "reply": reply,
            "face": face,
            "affection_delta": affection_delta,
            "tags": tags,
            "flags_set": flags_set,
            "memory_1line": memory_1line,
        }

    def chat(self, message: str, history: list[dict[str, str]]) -> dict[str, Any]:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(history)
        messages.append({"role": "user", "content": message})

        extra_body: dict[str, Any] = {
            "guided_json": SCHEMA,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        if settings.llm_top_k > 0:
            extra_body["top_k"] = settings.llm_top_k

        response = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=settings.llm_max_tokens,
            temperature=settings.llm_temperature,
            top_p=settings.llm_top_p,
            extra_body=extra_body,
        )

        raw = response.choices[0].message.content or ""
        raw_json = self._extract_json_object(raw)
        parsed = json.loads(raw_json)
        return self._normalize(parsed)
