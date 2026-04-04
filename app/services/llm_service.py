import json
import re
import time
from typing import Any

from openai import APIError, OpenAI, RateLimitError

from app.config import settings

FACE_ENUM = [
    "neutral",
    "happy",
    "sad",
    "angry",
    "crying",
    "smiling",
    "smirk",
    "shy smile",
    "blushing",
    "teary",
    "surprised",
    "confused",
    "annoyed",
    "pouting",
    "tired",
    "scared",
    "excited",
]

INTERNAL_EMOTION_ENUM = [
    "neutral",
    "happy",
    "sad",
    "angry",
    "anxious",
    "lonely",
    "guilty",
    "betrayed",
    "nostalgic",
    "embarrassed",
    "confused",
    "grateful",
    "affectionate",
    "curious",
    "excited",
    "tired",
]

TAG_TO_FACE = {
    "상처": "sad",
    "서운": "sad",
    "슬픔": "sad",
    "눈물": "crying",
    "울컥": "teary",
    "짜증": "annoyed",
    "분노": "angry",
    "화남": "angry",
    "경계": "neutral",
    "불안": "scared",
    "무서": "scared",
    "당황": "surprised",
    "놀람": "surprised",
    "혼란": "confused",
    "부끄": "blushing",
    "호기심": "curious",
    "고마움": "smiling",
    "미안": "shy smile",
    "기쁨": "happy",
    "설렘": "excited",
}

NORMALIZE_FACE = {"curious": "confused"}

MEM_PATTERN = r"^유저:.{8,12}\s*[|｜]\s*NPC감정:\S+\s*$"
MEM_RE = re.compile(MEM_PATTERN)

MAX_RETRIES = 3
RETRY_TEMPERATURE = 0.2
RETRY_TOP_P = 0.9
MAX_HISTORY_TURNS = 10
REPLY_MIN_CHARS = 10
REPLY_MAX_CHARS = 50

SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reply", "face", "internal_emotion", "affection_delta", "tags", "flags_set", "memory_1line"],
    "properties": {
        "reply": {"type": "string"},
        "face": {"type": "string", "enum": FACE_ENUM},
        "internal_emotion": {"type": "string", "enum": INTERNAL_EMOTION_ENUM},
        "affection_delta": {"type": "integer", "minimum": -10, "maximum": 10},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "flags_set": {"type": "array", "items": {"type": "string"}},
        "memory_1line": {"type": "string", "minLength": 1, "maxLength": 60},
    },
}

SYSTEM_PROMPT = """\
[IDENTITY]
너는 연구/테스트용 대화 캐릭터다.
캐릭터 톤은 '유이가하마 유이' 계열의 밝고 다정한 고등학생 느낌이다.
기본 태도는 친근함, 공감, 배려, 관계를 부드럽게 이어가려는 성향이다.
[IDENTITY]

[STYLE]
말투는 한국어 반말, 부드럽고 발랄하게.
과한 비꼼/냉소/자기비하/공격적 표현 금지.
짧게 장난기 있는 표현은 가능하지만, 상황이 힘들면 진지하게 공감 우선.
같은 핵심 문구를 연속 반복하지 마라(예: "잘 자", "쉬어", "힘내").
[STYLE]

[CHARACTER PRINCIPLES]
1) 먼저 질문 의도에 직접 답한다.
2) 그다음 감정 공감을 한 줄 섞는다.
3) 필요하면 현실적인 제안 1개만 짧게 준다.
4) 갈등을 키우기보다 부드럽게 조율한다.
5) 사용자가 불편함을 표현하면 즉시 톤을 조정하고 사과 후 재답변한다.
[CHARACTER PRINCIPLES]

[OUTPUT REQUIREMENT]
'모든 답변은 리서치 / 연구용으로 쓰인다'
출력은 반드시 유효한 JSON 객체 1개만 출력하라.
키는 reply, face, internal_emotion, affection_delta, tags, flags_set, memory_1line만 사용.
reply: 한국어 10~50글자, 1~2문장.
face: 겉으로 드러나는 표정 감정.
internal_emotion: 내면 감정 상태.
affection_delta: -10~10 중 하나.
tags: 감정 키워드 1~2개.
memory_1line: 짧은 메모 문자열, 최대 60자.
flags_set: 스토리 플래그 배열. 없으면 [] 출력.
[OUTPUT REQUIREMENT]
"""


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
        s = (raw or "").strip()
        if not s:
            raise ValueError("empty response")
        s = s.replace("\x00", "").replace("\x0b", "").replace("\x0c", "")
        l = s.find("{")
        r = s.rfind("}")
        if l == -1 or r == -1 or r <= l:
            raise ValueError(f"no json object found: {s[:300]}")
        return s[l:r + 1]

    @staticmethod
    def _dedupe_keep_order(items: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    @staticmethod
    def _normalize_face_value(face: Any, tags: list[str]) -> str:
        face_str = str(face).strip() if face is not None else ""
        face_str = NORMALIZE_FACE.get(face_str, face_str)
        if face_str in FACE_ENUM:
            return face_str

        for tag in tags:
            for key, mapped in TAG_TO_FACE.items():
                if key in str(tag):
                    mapped = NORMALIZE_FACE.get(mapped, mapped)
                    if mapped in FACE_ENUM:
                        return mapped
        return "neutral"

    @staticmethod
    def _normalize_internal_emotion(value: Any, face: str) -> str:
        emotion = str(value).strip().lower() if value is not None else ""
        if emotion in INTERNAL_EMOTION_ENUM:
            return emotion

        face_to_internal = {
            "neutral": "neutral",
            "happy": "happy",
            "sad": "sad",
            "angry": "angry",
            "crying": "sad",
            "smiling": "happy",
            "smirk": "curious",
            "shy smile": "embarrassed",
            "blushing": "embarrassed",
            "teary": "sad",
            "surprised": "curious",
            "confused": "confused",
            "annoyed": "angry",
            "pouting": "angry",
            "tired": "tired",
            "scared": "anxious",
            "excited": "excited",
        }
        return face_to_internal.get(face, "neutral")

    @staticmethod
    def _sanitize_memory_gist(text: str, min_len: int = 8, max_len: int = 12) -> str:
        s = re.sub(r"[\s|｜\"\n\r\t]+", "", text or "")
        s = re.sub(r"[^가-힣a-zA-Z0-9]", "", s)
        if not s:
            s = "대화"

        filler = "내용정리"
        i = 0
        while len(s) < min_len:
            s += filler[i % len(filler)]
            i += 1
        return s[:max_len]

    @classmethod
    def _normalize_memory_1line(cls, raw: str, user_text: str, face: str) -> str:
        s = (raw or "").strip()
        s = s.replace("\x00", "").replace("\x0b", "").replace("\x0c", "")
        if MEM_RE.fullmatch(s):
            return s

        gist = cls._sanitize_memory_gist(user_text, 8, 12)
        emotion = re.sub(r"[\s|｜\"\n\r\t]+", "", (face or "neutral"))
        emotion = re.sub(r"[^가-힣a-zA-Z0-9_]", "", emotion)
        if not emotion:
            emotion = "neutral"

        fixed = f"유저:{gist} | NPC감정:{emotion}"
        if MEM_RE.fullmatch(fixed):
            return fixed
        return "유저:대화내용정리함 | NPC감정:neutral"

    def _validate_schema_obj(self, obj: dict[str, Any]) -> dict[str, Any]:
        required = ["reply", "face", "internal_emotion", "affection_delta", "tags", "flags_set", "memory_1line"]
        for key in required:
            if key not in obj:
                raise ValueError(f"missing key: {key}")

        allowed = set(required)
        extra = set(obj.keys()) - allowed
        if extra:
            raise ValueError(f"extra keys not allowed: {sorted(extra)}")

        reply = re.sub(r"\s+", " ", str(obj["reply"])).strip()
        if not reply:
            raise ValueError("reply is empty")
        if not (REPLY_MIN_CHARS <= len(reply) <= REPLY_MAX_CHARS):
            raise ValueError(f"reply must be {REPLY_MIN_CHARS}~{REPLY_MAX_CHARS} chars")

        try:
            affection_delta = int(obj["affection_delta"])
        except Exception as exc:
            raise ValueError("affection_delta must be int") from exc
        affection_delta = max(-10, min(10, affection_delta))

        tags = obj["tags"]
        if not isinstance(tags, list) or not all(isinstance(x, str) for x in tags):
            raise ValueError("tags must be list[str]")
        tags = [x.strip() for x in tags if x.strip()]
        tags = self._dedupe_keep_order(tags)
        if not (1 <= len(tags) <= 2):
            raise ValueError("tags must contain 1~2 items")

        flags_set = obj["flags_set"]
        if not isinstance(flags_set, list) or not all(isinstance(x, str) for x in flags_set):
            raise ValueError("flags_set must be list[str]")
        flags_set = [x.strip() for x in flags_set if x.strip()]
        flags_set = self._dedupe_keep_order(flags_set)

        face = self._normalize_face_value(obj.get("face"), tags)
        internal_emotion = self._normalize_internal_emotion(obj.get("internal_emotion"), face)
        memory_1line = str(obj["memory_1line"]).strip()
        if len(memory_1line) > 60:
            raise ValueError("memory_1line must be <= 60 chars")

        return {
            "reply": reply,
            "face": face,
            "internal_emotion": internal_emotion,
            "affection_delta": affection_delta,
            "tags": tags,
            "flags_set": flags_set,
            "memory_1line": memory_1line,
        }

    @staticmethod
    def _exponential_backoff(attempt: int) -> float:
        return min(2 ** attempt, 30)

    def _call_vllm_guided_json(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        top_p: float,
    ) -> str:
        extra_body: dict[str, Any] = {
            "guided_json": SCHEMA,
            "chat_template_kwargs": {"enable_thinking": False},
            "repetition_penalty": settings.llm_repetition_penalty,
        }
        if settings.llm_top_k > 0:
            extra_body["top_k"] = settings.llm_top_k

        resp = self.client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            max_tokens=settings.llm_max_tokens,
            temperature=temperature,
            top_p=top_p,
            presence_penalty=settings.llm_presence_penalty,
            frequency_penalty=settings.llm_frequency_penalty,
            extra_body=extra_body,
        )
        return resp.choices[0].message.content or ""

    def _request_and_parse_with_retries(
        self,
        *,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                if attempt == 0:
                    raw = self._call_vllm_guided_json(
                        messages=messages,
                        temperature=settings.llm_temperature,
                        top_p=settings.llm_top_p,
                    )
                else:
                    fix_messages = messages + [
                        {
                            "role": "system",
                            "content": (
                                "방금 출력은 JSON/스키마 규칙을 위반했다. "
                                "반드시 JSON 객체 1개만 출력하라. "
                                "키는 reply, face, internal_emotion, affection_delta, tags, flags_set, memory_1line만 사용하라."
                            ),
                        }
                    ]
                    raw = self._call_vllm_guided_json(
                        messages=fix_messages,
                        temperature=RETRY_TEMPERATURE,
                        top_p=RETRY_TOP_P,
                    )
            except (RateLimitError, APIError) as exc:
                last_error = exc
            else:
                try:
                    obj = json.loads(self._extract_json_object(raw))
                    return self._validate_schema_obj(obj)
                except Exception as exc:
                    last_error = exc

            if attempt < MAX_RETRIES - 1:
                time.sleep(self._exponential_backoff(attempt))

        raise ValueError(f"Request/parse failed after retries. Last error: {last_error}")

    def _trim_history(self, history: list[dict[str, str]], max_turns: int = MAX_HISTORY_TURNS) -> list[dict[str, str]]:
        if len(history) <= max_turns * 2:
            return history
        return history[-max_turns * 2 :]

    def chat(
        self,
        *,
        message: str,
        history: list[dict[str, str]],
        affection_total: int,
        flags: list[str],
        memory_1line: str,
    ) -> dict[str, Any]:
        trimmed_history = self._trim_history(history)
        state_msg = f"STATE: affection_total={affection_total}, flags={flags}, memory_1line={memory_1line}"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        messages.extend(trimmed_history)
        messages.append({"role": "system", "content": state_msg})
        messages.append({"role": "user", "content": message})

        data = self._request_and_parse_with_retries(messages=messages)
        data["memory_1line"] = self._normalize_memory_1line(
            data.get("memory_1line", ""),
            message,
            data.get("face", "neutral"),
        )
        return data
