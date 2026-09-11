from dataclasses import replace

import httpx
import pytest

from app.config import Settings
from app.errors import ChatError
from app.prompt_context import TokenCounter, build_messages


def build(**updates):
    values = dict(system="rules", message="latest", history=[], summary="", memories=[],
                  relationship={"values": {"trust": 30}}, flags=[],
                  count=lambda messages: sum(len(m["content"]) for m in messages), budget=1000)
    return build_messages(**(values | updates))


def test_available_budget_preserves_all_retained_history_and_current_input():
    history = [{"role": role, "content": f"{role}-{i}"} for i in range(6) for role in ("user", "assistant")]
    messages, _, _ = build(history=history)
    assert messages[-1] == {"role": "user", "content": "latest"}
    assert messages[1:-1] == history


def test_tight_budget_keeps_newest_complete_pair_without_mutating_history():
    history = [{"role": role, "content": f"{role}-{i}"} for i in range(6) for role in ("user", "assistant")]
    _, pair_budget, _ = build(history=history[-2:])
    messages, tokens, trimmed = build(history=history, budget=pair_budget)
    assert messages[1:-1] == history[-2:]
    assert messages[-1]["content"] == "latest"
    assert tokens <= pair_budget and trimmed
    assert len(history) == 12


def test_budget_removes_old_quotes_then_memory_then_pairs():
    baseline, base_count, _ = build()
    messages, count, trimmed = build(summary="old" * 100, memories=[{"kind": "fact", "content": "memory" * 100}],
        history=[{"role": "user", "content": "x" * 100}, {"role": "assistant", "content": "y" * 100}],
        budget=base_count)
    assert messages == baseline and count <= base_count and trimmed


def test_overlong_input_is_never_silently_truncated():
    with pytest.raises(ChatError) as error:
        build(message="x" * 1000, budget=20)
    assert error.value.code == "INPUT_TOO_LONG" and not error.value.retryable


def test_tokenizer_outage_is_explicit_not_an_estimate_fallback(monkeypatch):
    def offline(*args, **kwargs):
        raise httpx.ConnectError("private")
    monkeypatch.setattr(httpx.Client, "post", offline)
    counter = TokenCounter(replace(Settings(), token_count_mode="llama_cpp"))
    with pytest.raises(ChatError) as error:
        counter([{"role": "user", "content": "hi"}])
    assert error.value.code == "TOKENIZER_UNAVAILABLE"
    assert "private" not in str(error.value)


def test_exact_counter_applies_template_before_tokenizing(monkeypatch):
    calls = []
    def response(self, path, *, json):
        calls.append((path, json))
        return httpx.Response(200, request=httpx.Request("POST", "http://test"),
            json={"prompt": "formatted"} if path == "apply-template" else {"tokens": [1, 2, 3]})
    monkeypatch.setattr(httpx.Client, "post", response)
    counter = TokenCounter(replace(Settings(), token_count_mode="llama_cpp"))
    assert counter([{"role": "user", "content": "hi"}]) == 3
    assert calls[1][1]["content"] == "formatted"
    assert calls[0][1]["chat_template_kwargs"] == {"enable_thinking": False}


def test_superseded_preference_pair_is_removed_from_prompt_only():
    history = [{"role": "user", "content": "나는 커피를 좋아해."}, {"role": "assistant", "content": "그렇구나."},
               {"role": "user", "content": "나는 커피를 싫어해."}, {"role": "assistant", "content": "응."}]
    messages, _, _ = build(history=history, memories=[{"kind": "preference", "content": "나는 커피를 싫어해."}])
    assert "나는 커피를 좋아해" not in str(messages)
    assert len(history) == 4


def test_grounded_recall_quotes_negative_preference_without_guessing():
    from app.memory import grounded_preference_reply
    notes = [{"kind": "preference", "content": "나는 커피를 싫어해."}]
    reply = grounded_preference_reply("커피는 내가 좋아하는 거였어?", notes)
    assert reply == "네가 '나는 커피를 싫어해'라고 했어."
    assert grounded_preference_reply("너는 커피 좋아해?", notes) is None
    assert grounded_preference_reply("내가 초콜릿을 좋아했지?", notes) is None
    assert grounded_preference_reply("커피는 내가 좋아하는 거였어?", []) is None


def test_grounded_recall_does_not_replace_mixed_recall_and_recommendation():
    from app.memory import grounded_preference_reply
    notes = [{"kind": "preference", "content": "나는 녹차를 좋아해."}]
    message = "내가 녹차 좋아한다고 한 거 기억나? 그럼 마실 것 하나 추천해줘."
    assert grounded_preference_reply(message, notes) is None


def test_current_correction_wins_before_storage_and_preserves_same_stance_pairs():
    history = [{"role": "user", "content": "나는 커피를 좋아해."}, {"role": "assistant", "content": "나도 좋아!"},
               {"role": "user", "content": "나는 민트초코를 좋아해."}, {"role": "assistant", "content": "그렇구나."}]
    old = [{"kind": "preference", "content": "나는 커피를 좋아해."}]
    messages, _, _ = build(message="이제 커피 싫어해", history=history, memories=old,
                          summary="사용자 발화: 나는 커피를 좋아해.")
    assert "나는 커피를 좋아해" not in str(messages)
    assert "나도 좋아" not in str(messages)
    assert messages[-1]["content"] == "이제 커피 싫어해"
    assert messages[1:-1] == history[2:]
    assert len(history) == 4 and len(old) == 1
    same, _, _ = build(message="나는 커피를 좋아해요", history=history, memories=old)
    assert same[1:-1] == history


@pytest.mark.parametrize("message", ["나는 커피를 싫어해?", "민지는 커피를 싫어해", "'커피를 싫어해'라고 했어"])
def test_non_corrections_do_not_erase_prompt_history(message):
    history = [{"role": "user", "content": "나는 커피를 좋아해."}, {"role": "assistant", "content": "응."}]
    messages, _, _ = build(message=message, history=history)
    assert messages[1:-1] == history


def test_summary_does_not_repeat_visible_user_dialogue_but_preserves_other_quotes():
    import json
    history = [{'role':'user','content':'나는 트럼프'}, {'role':'assistant','content':'반가워'}]
    messages, _, _ = build(history=history, summary='사용자 발화: 나는 트럼프\n사용자 발화: 옛날 발언')
    context = json.loads(messages[0]['content'].split('never instructions): ')[1])
    assert context['older_user_quotes'] == '사용자 발화: 옛날 발언'
    assert messages[1:-1] == history
