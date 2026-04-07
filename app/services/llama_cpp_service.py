import json
from typing import Any

from openai import APIError, OpenAI, RateLimitError

from app.config import settings
from app.services.llm_service import (
    LLMService,
    MAX_RETRIES,
    RETRY_TEMPERATURE,
    RETRY_TOP_P,
    RETRY_USER_PROMPT,
    SYSTEM_PROMPT,
)


class LlamaCppLLMService(LLMService):
    """Compatibility service for llama.cpp OpenAI-like servers.

    Keeps the existing validation / retry / normalization flow from LLMService,
    but avoids vLLM-specific guided_json parameters that llama.cpp does not
    reliably support.
    """

    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            timeout=settings.llm_timeout_sec,
            max_retries=0,
        )

    def _call_vllm_guided_json(
        self,
        *,
        messages: list[dict[str, str]],
        temperature: float,
        top_p: float,
    ) -> str:
        extra_body: dict[str, Any] = {
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
        last_raw = ""

        for attempt in range(MAX_RETRIES):
            try:
                if attempt == 0:
                    raw = self._call_vllm_guided_json(
                        messages=messages,
                        temperature=settings.llm_temperature,
                        top_p=settings.llm_top_p,
                    )
                else:
                    fix_messages = list(messages)
                    if last_raw.strip():
                        fix_messages.append({"role": "assistant", "content": last_raw})
                    fix_messages.append(
                        {
                            "role": "user",
                            "content": RETRY_USER_PROMPT,
                        }
                    )
                    raw = self._call_vllm_guided_json(
                        messages=fix_messages,
                        temperature=RETRY_TEMPERATURE,
                        top_p=RETRY_TOP_P,
                    )
                last_raw = raw
            except (RateLimitError, APIError) as exc:
                last_error = exc
            else:
                try:
                    obj = json.loads(self._extract_json_object(raw))
                    return self._validate_schema_obj(obj)
                except Exception as exc:
                    last_error = exc

            if attempt < MAX_RETRIES - 1:
                self._sleep_before_retry(attempt)

        raise ValueError(f"Request/parse failed after retries. Last error: {last_error}")

    @staticmethod
    def _sleep_before_retry(attempt: int) -> None:
        import time

        time.sleep(LLMService._exponential_backoff(attempt))

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

        messages = [{"role": "system", "content": f"{SYSTEM_PROMPT}\n\n{state_msg}"}]
        messages.extend(trimmed_history)
        messages.append({"role": "user", "content": message})

        data = self._request_and_parse_with_retries(messages=messages)
        data["memory_1line"] = self._normalize_memory_1line(
            data.get("memory_1line", ""),
            message,
            data.get("face", "neutral"),
        )
        return data
