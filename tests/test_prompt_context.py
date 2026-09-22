from dataclasses import replace

import httpx
import pytest

from app.config import Settings
from app.errors import ChatError
from app.prompt_context import TokenCounter, build_messages, compact_metadata_context


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


def test_last_complete_pair_is_kept_before_general_memory():
    history = [{"role": "user", "content": "보리가 밥을 안 먹어."},
               {"role": "assistant", "content": "언제부터 그랬어?"}]
    memories = [{"kind": "fact", "content": "오래된 장기 기억" * 8}]
    _, history_count, _ = build(history=history)
    _, memory_count, _ = build(memories=memories)
    messages, tokens, trimmed = build(history=history, memories=memories,
                                      budget=max(history_count, memory_count))
    assert messages[1:-1] == history
    assert "오래된 장기 기억" not in messages[0]["content"]
    assert tokens <= max(history_count, memory_count) and trimmed


def test_oversized_source_evidence_is_pruned_before_short_input_fails():
    import json
    evidence = [{"kind": "episode", "content": json.dumps({
        "type": "proposal_or_promise_statement", "actor": "user",
        "quote": "긴 근거 " * 1000, "source_turn": "old",
    }, ensure_ascii=False)}]
    baseline, budget, _ = build()
    messages, tokens, trimmed = build(memories=evidence, budget=budget)
    assert messages == baseline
    assert tokens <= budget and trimmed


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
    assert counter.request_count == 2


def test_exact_counter_reuses_connection_and_caches_only_inside_request_scope(monkeypatch):
    clients = []
    class FakeClient:
        def __init__(self, **_kwargs):
            self.closed = False
            clients.append(self)
        def post(self, path, *, json):
            return httpx.Response(200, request=httpx.Request("POST", "http://test"),
                json={"prompt": "formatted"} if path == "apply-template" else {"tokens": [1, 2, 3]})
        def close(self):
            self.closed = True
    monkeypatch.setattr("app.prompt_context.httpx.Client", FakeClient)
    counter = TokenCounter(replace(Settings(), token_count_mode="llama_cpp"))
    messages = [{"role": "user", "content": "합성 입력"}]
    with counter.request_scope():
        assert counter(messages) == counter(messages) == 3
        assert counter.request_count == 2 and counter.cache_hits == 1
    assert counter._request_cache.get() is None
    assert counter(messages) == 3
    assert counter.request_count == 4 and len(clients) == 1
    counter.close()
    assert clients[0].closed
    assert counter(messages) == 3 and len(clients) == 2
    counter.close()


def test_request_cache_never_merges_different_message_content(monkeypatch):
    calls = []
    def response(self, path, *, json):
        calls.append((path, json))
        return httpx.Response(200, request=httpx.Request("POST", "http://test"),
            json={"prompt": json["messages"][0]["content"]} if path == "apply-template"
            else {"tokens": list(range(len(json["content"])))})
    monkeypatch.setattr(httpx.Client, "post", response)
    counter = TokenCounter(replace(Settings(), token_count_mode="llama_cpp"))
    try:
        with counter.request_scope():
            first = counter([{"role": "user", "content": "a"}])
            second = counter([{"role": "user", "content": "different"}])
        assert first != second and len(calls) == 4 and counter.cache_hits == 0
    finally:
        counter.close()


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


def test_compact_metadata_context_keeps_two_complete_pairs_and_source_evidence_only():
    history = [
        {"role": "assistant", "content": "불완전 시작"},
        *[{"role": role, "content": f"{role}-{number}"}
          for number in range(3) for role in ("user", "assistant")],
        {"role": "user", "content": "답 없는 과거 질문"},
    ]
    context = compact_metadata_context({
        "message": "현재 발언", "history": history, "memory_1line": "오래된 요약",
        "flags": ["known"], "relationship": {"stage": "friend"},
        "memories": [
            {"kind": "preference", "content": "일반 기억"},
            {"kind": "profile", "content": "이름 근거"},
            {"kind": "episode", "content": "사건 근거"},
        ],
    })
    assert context["message"] == "현재 발언"
    assert context["history"] == history[3:7]
    assert context["memory_1line"] == ""
    assert [item["kind"] for item in context["memories"]] == ["profile", "episode"]
    assert context["flags"] == ["known"] and context["relationship"] == {"stage": "friend"}
