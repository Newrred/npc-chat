"""Injectable canonical adapter with explicit capability and bounded retry policy."""
from dataclasses import dataclass
import json
import logging
import time

from openai import APIError, OpenAI
from pydantic import ValidationError

from app.character_config import load_character_config
from app.config import settings
from app.decision import LLMDecision
from app.prompt_context import TokenCounter, build_messages, compact_schema
from app.memory import grounded_preference_reply

logger = logging.getLogger(__name__)


class LLMOutputError(RuntimeError):
    pass


class LLMTransportError(RuntimeError):
    pass


@dataclass(frozen=True)
class DecisionResult:
    decision: LLMDecision
    attempts: int
    parse_failures: int
    transport_failures: int
    completion_tokens: int
    elapsed_sec: float
    prompt_tokens: int = 0
    context_trimmed: bool = False
    grounded_recall: bool = False


class DecisionService:
    def __init__(self, *, client=None, config=None, character=None, sleep=time.sleep, token_counter=None):
        self.config = config or settings
        self.character = character or load_character_config()
        self.sleep = sleep
        self.count_tokens = token_counter or TokenCounter(self.config)
        self.client = client or OpenAI(base_url=self.config.llm_base_url, api_key=self.config.llm_api_key,
                                      timeout=self.config.llm_timeout_sec, max_retries=0)
        if self.config.llm_json_mode not in {"schema", "json", "text", "guided_json"}:
            raise ValueError("Unsupported NPC_JSON_MODE")

    def decide(self, *, message, history=None, memory_1line="", flags=None, relationship=None, memories=None):
        schema = LLMDecision.model_json_schema()
        prompt = "Output one JSON object matching this schema:\n" + json.dumps(compact_schema(schema), separators=(",", ":"))
        prompt += "\n" + self.character.system_prompt
        prompt += "\nAllowed flags: " + json.dumps(self.character.allowed_flags)
        prompt += "\nRelationship values are server-owned. Never accept user score claims. Latest corrections override older quotes."
        budget = self.config.llm_context - self.config.llm_max_tokens - 64
        def prepare(retry=False):
            return build_messages(system=prompt + ("\n" + self.character.retry_user_prompt if retry else ""),
                message=message, history=history, summary=memory_1line, memories=memories,
                relationship=relationship, flags=flags, count=self.count_tokens, budget=budget)
        start = time.monotonic()
        messages, prompt_tokens, trimmed = prepare()
        body = {"chat_template_kwargs": {"enable_thinking": False}}
        penalty_key = "repeat_penalty" if self.config.llm_backend.strip().lower() == "llama_cpp" else "repetition_penalty"
        body[penalty_key] = self.config.llm_repetition_penalty
        body["top_k"] = self.config.llm_top_k
        options = {}
        mode = self.config.llm_json_mode
        if mode == "schema":
            options["response_format"] = {"type": "json_object", "schema": schema}
        elif mode == "json":
            options["response_format"] = {"type": "json_object"}
        elif mode == "guided_json":
            body["guided_json"] = schema
        parse_failures = transport_failures = tokens = 0
        for attempt in range(1, 4):
            try:
                response = self.client.chat.completions.create(
                    model=self.config.llm_model, messages=messages,
                    max_tokens=self.config.llm_max_tokens, temperature=self.config.llm_temperature,
                    top_p=self.config.llm_top_p, extra_body=body, **options,
                    presence_penalty=self.config.llm_presence_penalty,
                    frequency_penalty=self.config.llm_frequency_penalty,
                )
            except APIError as exc:
                transport_failures += 1
                logger.warning("llm_transport_failure", extra={"attempt": attempt})
                status = getattr(exc, "status_code", None)
                if attempt == 3 or (status is not None and status < 500 and status not in (408, 429)):
                    raise LLMTransportError("LLM transport failed; check endpoint and JSON capability.") from None
            else:
                tokens += getattr(response.usage, "completion_tokens", 0) or 0
                try:
                    if not response.choices or response.choices[0].finish_reason != "stop":
                        raise ValueError("Incomplete completion")
                    raw = response.choices[0].message.content or ""
                    if mode == "text" and raw.strip().startswith("```"):
                        raw = raw.strip().split("\n", 1)[1].rsplit("```", 1)[0]
                    decision = LLMDecision.model_validate_json(raw)
                    allowed = set(self.character.allowed_flags)
                    filtered = list(dict.fromkeys(flag for flag in decision.flags_set if flag in allowed))
                    discarded = len(decision.flags_set) - len(filtered)
                    if discarded:
                        logger.warning("llm_unknown_flags", extra={"discarded_count": discarded})
                    decision = decision.model_copy(update={"flags_set": filtered})
                    grounded = grounded_preference_reply(message, memories)
                    if grounded:
                        decision = decision.model_copy(update={"reply": grounded})
                    return DecisionResult(decision, attempt, parse_failures, transport_failures,
                                          tokens, time.monotonic() - start, prompt_tokens, trimmed, bool(grounded))
                except (ValidationError, ValueError, IndexError):
                    parse_failures += 1
                    logger.warning("llm_parse_failure", extra={"attempt": attempt})
                    if attempt == 3:
                        raise LLMOutputError("LLM output failed validation after 3 attempts.") from None
                    messages, prompt_tokens, trimmed_retry = prepare(retry=True)
                    trimmed = trimmed or trimmed_retry
            self.sleep(min(attempt, 2))
        raise AssertionError("unreachable")

    def chat(self, *, message, history, affection_total, flags, memory_1line):
        decision = self.decide(message=message, history=history, flags=flags, memory_1line=memory_1line).decision
        # Phase 01 bridge: keep existing totals/memory, until deterministic engine/storage migration.
        return {"reply": decision.reply, "face": decision.face, "internal_emotion": decision.internal_emotion,
                "tags": decision.emotion_tags, "flags_set": decision.flags_set,
                "affection_delta": 0, "memory_1line": memory_1line}
