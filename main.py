# main.py
"""
NPC 대화형 캐릭터 시스템

vLLM OpenAI 호환 API를 사용하여 감정이 풍부한 NPC와 대화합니다.
구조화된 JSON 출력을 강제하여 일관된 응답 형식을 유지합니다.
"""

import argparse
import json
import logging
import os
import re
import time

from typing import Any, Callable, Dict, List, Optional, Tuple

from openai import OpenAI, APIError, RateLimitError

# ============================================================================
# 상수 정의
# ============================================================================

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

# tags -> face heuristic
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
    "호기심": "curious",   # normalize 단계에서 변환
    "고마움": "smiling",
    "미안": "shy smile",
    "기쁨": "happy",
    "설렘": "excited",
}

NORMALIZE_FACE = {
    "curious": "confused",
}

AFF_ENUM = list(range(-10, 11))

# 후처리용 memory 패턴 (모델에게 강제 X, 파이썬에서 맞춤)
MEM_PATTERN = r"^유저:.{8,12}\s*[|｜]\s*NPC감정:\S+\s*$"
MEM_RE = re.compile(MEM_PATTERN)

SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["reply", "face", "affection_delta", "tags", "flags_set", "memory_1line"],
    "properties": {
        "reply": {"type": "string"},
        "face": {"type": "string", "enum": FACE_ENUM},
        "affection_delta": {"type": "integer", "enum": AFF_ENUM},
        "tags": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "flags_set": {"type": "array", "items": {"type": "string"}},
        # 여기서 regex 강제하지 않음 (핵심)
        "memory_1line": {"type": "string", "minLength": 1, "maxLength": 60},
    },
}

SYSTEM_PROMPT = """\
당신은 감정이 풍부하고의 대화형 NPC이다.
중요: 사용자의 질문에는 먼저 자연스럽고 직접적으로 답한 뒤, 감정을 살짝 섞어라.
불필요한 반문, 문맥 없는 시니컬함, 이상한 자기비하를 금지한다. 말투는 반말로

출력은 반드시 "유효한 JSON 객체 1개"만. 다른 텍스트/설명/코드블록 금지.
키는 reply, face, affection_delta, tags, flags_set, memory_1line만 사용.

reply: 한국어 10~50글자. 1~2문장. 뻔한 위로/교과서 문장 금지.
face: 겉으로 드러나는 표정 감정.
affection_delta: -10~10 중 하나.
tags: 감정 키워드 1~2개
memory_1line: 짧은 메모 문자열만 출력. 최대 60자.
flags_set: 스토리 플래그 배열. 없으면 반드시 빈 배열 [] 출력.
"""

MAX_RETRIES = 3
RETRY_TEMPERATURE = 0.2
RETRY_TOP_P = 0.9
MAX_MEMORY_LENGTH = 100
MAX_REPLY_LENGTH = 500
MAX_HISTORY_TURNS = 10
LOG_LEVEL = os.getenv("NPC_LOG_LEVEL", "INFO")

# ============================================================================
# 로깅 설정
# ============================================================================

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ============================================================================
# 유틸리티 함수
# ============================================================================

def clamp_int(x: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, x))


def truncate_text(text: str, max_length: int) -> str:
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def exponential_backoff(attempt: int) -> float:
    return min(2 ** attempt, 30)


def _extract_json_object(raw: str) -> str:
    """
    응답에서 가장 바깥 JSON 객체를 추출.
    """
    s = (raw or "").strip()
    if not s:
        raise ValueError("empty response")

    # 제어문자 약간 정리
    s = s.replace("\x00", "").replace("\x0b", "").replace("\x0c", "")

    l = s.find("{")
    r = s.rfind("}")
    if l == -1 or r == -1 or r <= l:
        raise ValueError(f"no json object found: {s[:300]}")
    return s[l:r + 1]


def _dedupe_keep_order(items: List[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def normalize_face_value(face: Any, tags: List[str]) -> str:
    face_str = str(face).strip() if face is not None else ""
    face_str = NORMALIZE_FACE.get(face_str, face_str)

    if face_str in FACE_ENUM:
        return face_str

    for tag in tags or []:
        tag_str = str(tag)
        for key, mapped in TAG_TO_FACE.items():
            if key in tag_str:
                mapped = NORMALIZE_FACE.get(mapped, mapped)
                if mapped in FACE_ENUM:
                    return mapped

    return "neutral"


def sanitize_memory_gist(text: str, min_len: int = 8, max_len: int = 12) -> str:
    """
    user_text를 memory용 8~12자 요약 문자열로 강제 맞춤.
    """
    s = re.sub(r'[\s|｜"\n\r\t]+', "", text or "")
    s = re.sub(r"[^가-힣a-zA-Z0-9]", "", s)

    if not s:
        s = "대화"

    filler = "내용정리"
    i = 0
    while len(s) < min_len:
        s += filler[i % len(filler)]
        i += 1

    return s[:max_len]


def normalize_memory_1line(raw: str, user_text: str, tags: List[str]) -> str:
    """
    모델 출력이 형식에 안 맞아도, Python에서 강제로
    '유저:XXXXXXXX | NPC감정:YYY' 형태로 고정.
    """
    s = (raw or "").strip()
    s = s.replace("\x00", "").replace("\x0b", "").replace("\x0c", "")

    if MEM_RE.fullmatch(s):
        return s

    gist = sanitize_memory_gist(user_text, 8, 12)

    emotion = (tags[0] if tags else "혼란").strip()
    emotion = re.sub(r'[\s|｜"\n\r\t]+', "", emotion)
    emotion = re.sub(r"[^가-힣a-zA-Z0-9]", "", emotion)

    if not emotion:
        emotion = "혼란"

    fixed = f"유저:{gist} | NPC감정:{emotion}"
    if MEM_RE.fullmatch(fixed):
        return fixed

    return "유저:대화내용정리함 | NPC감정:혼란"


def build_error_payload(message: str) -> Dict[str, Any]:
    return {
        "reply": truncate_text(f"[오류: {message}]", MAX_REPLY_LENGTH),
        "face": "neutral",
        "affection_delta": 0,
        "tags": ["오류"],
        "flags_set": [],
        "memory_1line": "오류발생",
    }


def validate_schema_obj(obj: Dict[str, Any]) -> Dict[str, Any]:
    # required 키 검증
    for key in SCHEMA["required"]:
        if key not in obj:
            raise ValueError(f"missing key: {key}")

    # 추가 키 방지
    allowed = set(SCHEMA["required"])
    extra = set(obj.keys()) - allowed
    if extra:
        raise ValueError(f"extra keys not allowed: {sorted(extra)}")

    # reply
    if not isinstance(obj["reply"], str):
        raise ValueError("reply must be string")
    obj["reply"] = obj["reply"].strip()
    if not obj["reply"]:
        raise ValueError("reply is empty")

    # memory_1line (여기서는 비어있지만 않으면 됨)
    if not isinstance(obj["memory_1line"], str):
        raise ValueError("memory_1line must be string")
    obj["memory_1line"] = obj["memory_1line"].strip()
    if not obj["memory_1line"]:
        raise ValueError("memory_1line is empty")

    # affection_delta
    if not isinstance(obj["affection_delta"], int):
        try:
            obj["affection_delta"] = int(obj["affection_delta"])
        except Exception as e:
            raise ValueError("affection_delta must be int") from e
    obj["affection_delta"] = clamp_int(obj["affection_delta"], -10, 10)

    # tags
    if not isinstance(obj["tags"], list):
        raise ValueError("tags must be list[str]")
    if not all(isinstance(x, str) for x in obj["tags"]):
        raise ValueError("tags must be list[str]")
    obj["tags"] = [x.strip() for x in obj["tags"] if x and x.strip()]
    obj["tags"] = _dedupe_keep_order(obj["tags"])
    if not (1 <= len(obj["tags"]) <= 2):
        raise ValueError("tags must contain 1~2 items")

    # flags_set
    if not isinstance(obj["flags_set"], list):
        raise ValueError("flags_set must be list[str]")
    if not all(isinstance(x, str) for x in obj["flags_set"]):
        raise ValueError("flags_set must be list[str]")
    obj["flags_set"] = [x.strip() for x in obj["flags_set"] if x and x.strip()]
    obj["flags_set"] = _dedupe_keep_order(obj["flags_set"])

    # face
    obj["face"] = normalize_face_value(obj.get("face"), obj["tags"])
    if obj["face"] not in FACE_ENUM:
        raise ValueError(f"invalid face: {obj['face']}")

    return obj

# ============================================================================
# vLLM API 호출
# ============================================================================

def call_vllm_guided_json(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    top_p: float,
    top_k: Optional[int],
) -> str:
    extra: Dict[str, Any] = {
        "guided_json": SCHEMA,
        "chat_template_kwargs": {"enable_thinking": False},
    }

    if top_k is not None:
        extra["top_k"] = top_k

    resp = client.chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        extra_body=extra,
    )

    choice = resp.choices[0]
    logger.info(f"finish_reason={choice.finish_reason}")

    content = choice.message.content
    return content or ""

# ============================================================================
# 요청 + 파싱 + 재시도 로직
# ============================================================================

def request_and_parse_with_retries(
    first_call: Callable[[], str],
    repair_call: Callable[[], str],
    max_retries: int = MAX_RETRIES,
) -> Tuple[Dict[str, Any], int]:
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        try:
            raw = first_call() if attempt == 0 else repair_call()
        except RateLimitError as e:
            last_error = e
            logger.warning(f"Rate limit on attempt {attempt + 1}/{max_retries}: {e}")
        except APIError as e:
            last_error = e
            logger.warning(f"API error on attempt {attempt + 1}/{max_retries}: {e}")
        else:
            try:
                json_str = _extract_json_object(raw)
                obj = json.loads(json_str)
                validated = validate_schema_obj(obj)
                logger.info(f"Turn parsing succeeded on attempt {attempt + 1}/{max_retries}")
                return validated, attempt
            except Exception as e:
                last_error = e
                logger.warning(f"JSON/schema validation failed on attempt {attempt + 1}/{max_retries}: {e}")

        if attempt < max_retries - 1:
            backoff = exponential_backoff(attempt)
            logger.info(f"Retrying in {backoff}s...")
            time.sleep(backoff)

    raise ValueError(f"Request/parse failed after {max_retries} attempts. Last error: {last_error}")

# ============================================================================
# 메인 함수
# ============================================================================

def parse_arguments() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="감정이 풍부한 NPC 대화 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python main.py --turns 5 --temp 0.3
  python main.py --base_url_v1 http://localhost:8000/v1 --model Qwen/Qwen3-4B-AWQ
        """,
    )
    ap.add_argument(
        "--base_url_v1",
        default=os.getenv("NPC_BASE_URL", "https://deputy-loaded-floral-cheque.trycloudflare.com/v1"),
        help="vLLM 서버 URL",
    )
    ap.add_argument(
        "--api_key",
        default=os.getenv("NPC_API_KEY", "my-local-key"),
        help="API 키",
    )
    ap.add_argument(
        "--model",
        default=os.getenv("NPC_MODEL", "Qwen/Qwen3-8B-AWQ"),
        help="모델 이름",
    )
    ap.add_argument(
        "--turns",
        type=int,
        default=int(os.getenv("NPC_TURNS", "10")),
        help="대화 턴 수 (기본: 10)",
    )
    ap.add_argument(
        "--max_tokens",
        type=int,
        default=int(os.getenv("NPC_MAX_TOKENS", "2048")),
        help="최대 생성 토큰 수 (기본: 2048)",
    )
    ap.add_argument(
        "--temp",
        type=float,
        default=float(os.getenv("NPC_TEMP", "0.4")),
        help="생성 온도 (기본: 0.4)",
    )
    ap.add_argument(
        "--top_p",
        type=float,
        default=float(os.getenv("NPC_TOP_P", "1.0")),
        help="nucleus sampling 확률 (기본: 1.0)",
    )
    ap.add_argument(
        "--top_k",
        type=int,
        default=int(os.getenv("NPC_TOP_K", "20")),
        help="top-k sampling (기본: 20, 0 이하면 비활성)",
    )
    ap.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("NPC_TIMEOUT", "120")),
        help="요청 타임아웃 (초, 기본: 120)",
    )
    ap.add_argument(
        "--log_level",
        default=os.getenv("NPC_LOG_LEVEL", "INFO"),
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="로그 레벨 (기본: INFO)",
    )
    ap.add_argument(
        "--output_file",
        default=os.getenv("NPC_OUTPUT_FILE", None),
        help="대화 기록을 저장할 파일 경로",
    )
    return ap.parse_args()


def save_conversation(
    output_file: str,
    history: List[Dict[str, str]],
    affection_total: int,
    flags: set,
    memory_1line: str,
) -> None:
    data = {
        "affection_total": affection_total,
        "flags": sorted(flags),
        "memory_1line": memory_1line,
        "conversation": history,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Conversation saved to {output_file}")


def cleanup_history(
    history: List[Dict[str, str]],
    max_turns: int = MAX_HISTORY_TURNS,
) -> List[Dict[str, str]]:
    system_messages = [m for m in history if m["role"] == "system"]
    dialogue_messages = [m for m in history if m["role"] in ("user", "assistant")]

    max_dialogue_messages = max_turns * 2
    if len(dialogue_messages) > max_dialogue_messages:
        dialogue_messages = dialogue_messages[-max_dialogue_messages:]

    new_history: List[Dict[str, str]] = []
    if system_messages:
        new_history.append(system_messages[0])
    new_history.extend(dialogue_messages)
    return new_history


def main() -> None:
    args = parse_arguments()

    logging.getLogger().setLevel(getattr(logging, args.log_level.upper(), logging.INFO))

    logger.info(f"Starting NPC conversation with model: {args.model}")
    logger.info(f"Parameters: turns={args.turns}, temp={args.temp}, max_tokens={args.max_tokens}")

    turns = args.turns
    if turns < 1:
        turns = 4
        logger.warning(f"Invalid turns value, using fallback: {turns}")

    affection_total = 0
    flags: set = set()
    memory_1line = ""

    history: List[Dict[str, str]] = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    client = OpenAI(
        base_url=args.base_url_v1,
        api_key=args.api_key,
        timeout=float(args.timeout),
        max_retries=0,
    )

    start_time = time.time()

    for t in range(1, turns + 1):
        user = input(f"\nUSER[{t}]> ").strip() or "..."

        state_msg = (
            f"STATE: affection_total={affection_total}, "
            f"flags={sorted(flags)}, "
            f"memory_1line={memory_1line}"
        )

        messages = history + [
            {"role": "system", "content": state_msg},
            {"role": "user", "content": user},
        ]

        top_k_value = args.top_k if args.top_k > 0 else None

        def first_call() -> str:
            return call_vllm_guided_json(
                client=client,
                model=args.model,
                messages=messages,
                max_tokens=args.max_tokens,
                temperature=args.temp,
                top_p=args.top_p,
                top_k=top_k_value,
            )

        def repair_call() -> str:
            fix_messages = messages + [
                {
                    "role": "system",
                    "content": (
                        "방금 출력은 스키마/JSON 규칙을 위반했다. "
                        "반드시 JSON 객체 1개만 다시 출력하라. "
                        "키는 reply, face, affection_delta, tags, flags_set, memory_1line만 사용하라. "
                        "memory_1line은 짧고 단순하게 출력하라."
                    ),
                }
            ]
            return call_vllm_guided_json(
                client=client,
                model=args.model,
                messages=fix_messages,
                max_tokens=args.max_tokens,
                temperature=RETRY_TEMPERATURE,
                top_p=RETRY_TOP_P,
                top_k=top_k_value,
            )

        try:
            data, retry_count = request_and_parse_with_retries(
                first_call=first_call,
                repair_call=repair_call,
                max_retries=MAX_RETRIES,
            )
            logger.info(f"Turn {t} completed (retries: {retry_count})")
        except Exception as e:
            logger.error(f"Turn {t} failed: {e}")
            data = build_error_payload(str(e))
            retry_count = 0

        delta = clamp_int(int(data["affection_delta"]), -10, 10)
        affection_total += delta

        new_flags = data.get("flags_set") or []
        flags.update(new_flags)

        reply = truncate_text((data.get("reply") or "").strip(), MAX_REPLY_LENGTH)
        face = data.get("face", "neutral")
        tags = data.get("tags", [])

        # 핵심: 모델 출력 그대로 쓰지 말고 후처리 고정
        memory_1line = normalize_memory_1line(
            data.get("memory_1line") or "",
            user,
            tags,
        )
        memory_1line = truncate_text(memory_1line, MAX_MEMORY_LENGTH)

        print(f"\nNPC[{t}]> {reply}  [face={face}]")
        print(f"DEBUG> delta={delta}, affection_total={affection_total}, tags={tags}, retries={retry_count}")
        print(f"DEBUG> memory_1line={memory_1line}")

        history += [
            {"role": "user", "content": user},
            {"role": "assistant", "content": reply},
        ]

        history = cleanup_history(history)

    elapsed_time = time.time() - start_time
    logger.info(f"Conversation completed in {elapsed_time:.2f} seconds")

    print("\n=== 대화 종료 ===")
    print(f"최종 호감도: {affection_total}")
    print(f"플래그: {sorted(flags)}")
    print(f"메모리 (1줄): {memory_1line}")

    if args.output_file:
        save_conversation(args.output_file, history, affection_total, flags, memory_1line)


if __name__ == "__main__":
    main()