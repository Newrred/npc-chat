from dataclasses import replace
import json

import httpx
from openai import OpenAI
import pytest
from pydantic import ValidationError

from app.character_config import CharacterConfig, load_character_config
from app.config import Settings
from app.decision import LLMDecision
from app.services.decision_service import DecisionService, LLMOutputError, LLMTransportError


def valid():
    return {"schema_version": 1, "reply": "안녕!", "face": "shy smile", "internal_emotion": "happy",
            "emotion_tags": ["기쁨"], "interaction": {"type": "neutral", "intensity": 0},
            "memory_candidates": [], "flags_set": []}


def test_canonical_normalization_and_short_reply():
    data = valid()
    data["reply"] = "  아\n  좋아 "
    result = LLMDecision.model_validate(data)
    assert result.face == "shy_smile" and result.reply == "아 좋아"
    assert "affection_delta" not in result.model_dump()


@pytest.mark.parametrize("field,value", [
    ("schema_version", True), ("schema_version", "1"), ("reply", " "), ("reply", "가" * 81),
    ("reply", 5), ("face", "bogus"), ("internal_emotion", "bogus"), ("emotion_tags", []),
    ("interaction", {"type": "neutral", "intensity": True}),
    ("interaction", {"type": "neutral", "intensity": "2"}),
    ("interaction", {"type": "neutral", "intensity": 4}),
    ("interaction", {"type": "neutral", "intensity": 0, "score": 3}),
    ("memory_candidates", [{"kind": "fact", "content": "", "importance": 0}]),
    ("memory_candidates", [{"kind": "fact", "content": "좋아", "importance": -1}]),
    ("memory_candidates", [{"kind": "guess", "content": "좋아", "importance": 0}]),
    ("memory_candidates", [{"kind": "fact", "content": "좋아", "importance": 0}] * 3),
    ("affection_total", 100),
])
def test_strict_rejection(field, value):
    data = valid()
    data[field] = value
    with pytest.raises(ValidationError):
        LLMDecision.model_validate(data)


def service(responses, mode="schema"):
    calls = []

    def handler(request):
        calls.append(json.loads(request.content))
        result = responses.pop(0)
        if isinstance(result, int):
            return httpx.Response(result, json={"error": {"message": "private provider details"}})
        content, reason = result if isinstance(result, tuple) else (json.dumps(result), "stop")
        return httpx.Response(200, json={
            "id": "test", "object": "chat.completion", "created": 0, "model": "local-model",
            "choices": [{"index": 0, "finish_reason": reason,
                         "message": {"role": "assistant", "content": content}}],
            "usage": {"completion_tokens": 100, "prompt_tokens": 10, "total_tokens": 110},
        })
    client = OpenAI(api_key="fake", base_url="http://model.test/v1", max_retries=0,
                    http_client=httpx.Client(transport=httpx.MockTransport(handler)))
    return DecisionService(client=client, config=replace(Settings(), llm_json_mode=mode), sleep=lambda _: None,
                           character=CharacterConfig("test", "Return JSON", "Retry JSON", ("known",))), calls


def test_retry_flags_metrics_and_no_private_diagnostics(caplog):
    data = valid()
    data["flags_set"] = ["known", "private-unknown"]
    adapter, calls = service([("private malformed", "stop"), data])
    try:
        result = adapter.decide(message="private user")
        assert result.attempts == 2 and result.parse_failures == 1
        assert result.decision.flags_set == ["known"]
        assert result.completion_tokens == 200
        assert "private" not in caplog.text
        assert calls[0]["response_format"]["schema"]["additionalProperties"] is False
        assert calls[0]["chat_template_kwargs"] == {"enable_thinking": False}
    finally:
        adapter.client.close()


@pytest.mark.parametrize('backend,key', [('llama_cpp', 'repeat_penalty'), ('vllm', 'repetition_penalty')])
@pytest.mark.parametrize('top_k', [0, 20])
def test_sampling_parameters_reach_transport_on_initial_and_retry(backend, key, top_k):
    adapter, calls = service([('malformed', 'stop'), valid()])
    adapter.config = replace(adapter.config, llm_backend=backend, llm_top_k=top_k,
                             llm_repetition_penalty=1.08, llm_presence_penalty=0.5,
                             llm_frequency_penalty=0.3)
    try:
        adapter.decide(message='ㅇ')
        assert len(calls) == 2
        for call in calls:
            assert call[key] == 1.08
            assert call['top_k'] == top_k
            assert call['presence_penalty'] == 0.5
            assert call['frequency_penalty'] == 0.3
            assert ('repetition_penalty' if key == 'repeat_penalty' else 'repeat_penalty') not in call
            assert call['chat_template_kwargs'] == {'enable_thinking': False}
    finally:
        adapter.client.close()


def test_default_identity_reaches_model_system_prompt_after_retry():
    adapter, calls = service([("malformed", "stop"), valid()])
    # Exercise the current 8K profile; token budget failure paths have separate tests.
    adapter.config = replace(adapter.config, llm_context=8192)
    adapter.character = load_character_config("default")
    try:
        adapter.decide(message="니 이름뭔데", history=[
            {"role": "user", "content": "너 이름이 뭐야?"},
            {"role": "assistant", "content": "아직 이름은 없어. NPC라고 불러줘."}])
        assert len(calls) == 2
        for call in calls:
            system = call["messages"][0]
            assert system["role"] == "system"
            assert "유이가하마 유이" in system["content"]
            assert "네 이름은 유이" in system["content"]
            assert "이전 대화" in system["content"]
            assert "고유 이름은 아직 정해지지" not in system["content"]
    finally:
        adapter.client.close()


@pytest.mark.parametrize("responses,error,count", [
    ([401], LLMTransportError, 1), ([400], LLMTransportError, 1),
    ([503, 503, 503], LLMTransportError, 3),
    ([("{}", "stop")] * 3, LLMOutputError, 3),
    ([(json.dumps(valid()), "length")] * 3, LLMOutputError, 3),
])
def test_bounded_failures(responses, error, count):
    adapter, calls = service(responses)
    try:
        with pytest.raises(error, match="LLM") as exc:
            adapter.decide(message="test")
        assert "private" not in str(exc.value) and len(calls) == count
    finally:
        adapter.client.close()


@pytest.mark.parametrize("mode", ["schema", "json", "text", "guided_json"])
def test_explicit_capability_and_bridge(mode):
    adapter, calls = service([valid()], mode)
    try:
        output = adapter.chat(message="안녕", history=[], affection_total=42, flags=[], memory_1line="기존 메모")
        assert output["affection_delta"] == 0 and output["memory_1line"] == "기존 메모"
        assert output["face"] == "shy_smile"
        assert ("response_format" in calls[0]) == (mode in {"schema", "json"})
        assert ("guided_json" in calls[0]) == (mode == "guided_json")
    finally:
        adapter.client.close()


def test_server_context_is_in_single_initial_system_message():
    adapter, calls = service([valid()])
    try:
        adapter.decide(message="안녕", relationship={"values": {"trust": 30}},
                       memory_1line="사용자 발화: 시험 공부", flags=["known"],
                       memories=[{"kind": "fact", "content": "공부"}])
        messages = calls[0]["messages"]
        assert [m["role"] for m in messages] == ["system", "user"]
        assert "Server context" in messages[0]["content"]
        assert "server-owned" in messages[0]["content"]
    finally:
        adapter.client.close()
