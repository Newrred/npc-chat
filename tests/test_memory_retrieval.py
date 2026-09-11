from copy import deepcopy

import pytest

from app.memory import accepted_candidates, preference_statement, retrieve
from app.decision import MemoryCandidate


def memory(key, content, kind="fact", updated=1, importance=1):
    return dict(key=key, content=content, kind=kind, updated=updated, importance=importance)


CAT = memory("cat", "나는 고양이 보리를 키워.")
COFFEE = memory("coffee", "나는 커피를 좋아해.", "preference", 2)
TRIP = memory("trip", "제주도 여행을 준비하고 있어.", updated=3)


def history(*utterances):
    return [dict(role="user", content=value) for value in utterances]


@pytest.mark.parametrize("query,expected", [
    ("보리가 뭐였지?", ["cat"]), ("고양이는 뭘 좋아할까?", ["cat"]),
    ("커피는 내가 좋아했지?", ["coffee"]), ("제주도로 여행 가고 싶다", ["trip"]),
    ("오늘 점심 뭐 먹지?", []), ("걔 진짜 웃기다", []), ("안녕", []),
    ("좋아해", []), ("보리차 좋아해?", []), ("내 취향 기억나?", ["coffee"]),
])
def test_direct_topics_and_no_unrelated_fill(query, expected):
    assert [row["key"] for row in retrieve([CAT, COFFEE, TRIP], query)] == expected


@pytest.mark.parametrize("query,context,expected", [
    ("걔 때문에 잠을 못 잤어", history("보리가 새벽마다 뛰어다녀"), ["cat"]),
    ("그거 아직 기억나?", history("커피 이야기 했었지"), ["coffee"]),
    ("오늘 점심 뭐 먹지?", history("보리가 새벽마다 뛰어다녀"), []),
    ("근데 그거 말고 점심 먹을까?", history("보리가 새벽마다 뛰어다녀"), []),
    ("커피 마실까?", history("보리가 새벽마다 뛰어다녀"), ["coffee"]),
    ("걔 진짜 웃기다", history("보리랑 커피 이야기"), []),
    ("걔 때문에 잠을 못 잤어", history("회사 다녀왔어"), []),
    ("걔 때문에 잠을 못 잤어", [dict(role="assistant", content="보리가 뛰어다녔니?")], []),
    ("걔 때문에 잠을 못 잤어", history("보리", "다른 주제", "다른 주제", "다른 주제", "다른 주제"), []),
    ("걔 때문에 잠을 못 잤어", history("보리", "점심 먹었어"), []),
])
def test_context_is_bounded_user_grounded_and_only_used_for_continuations(query, context, expected):
    original = deepcopy(context)
    assert [row["key"] for row in retrieve([CAT, COFFEE, TRIP], query, context)] == expected
    assert context == original


def test_relevance_before_recency_then_bounded_deterministic_ties():
    rows = [memory(str(i), "보리가 뛰어다녀", updated=100) for i in range(5)]
    rows.append(memory("strong", "고양이 보리가 뛰어다녀", updated=1))
    rows.append(memory("unrelated", "오늘 아주 행복해", updated=10000, importance=3))
    original = deepcopy(rows)
    assert [r["key"] for r in retrieve(rows, "고양이 보리")] == ["strong", "4", "3"]
    assert rows == original


@pytest.mark.parametrize("text,expected", [
    ("나는 커피를 좋아해.", ("커피", "positive")),
    ("이제 커피 싫어해", ("커피", "negative")),
    ("난 이제 커피는 안 좋아해.", ("커피", "negative")),
    ("커피를 좋아하지 않아", ("커피", "negative")),
    ("커피는 이제 싫어해", ("커피", "negative")),
    ("친구는 커피를 싫어해", None), ("나는 친구가 커피를 싫어해", None),
    ("너는 커피를 싫어해", None), ("커피를 싫어해?", None),
    ("나는 '커피를 싫어해'라고 말했어", None), ("내가 커피를 싫어하면?", None),
    ("커피를 좋아하는 척했어", None), ("나는 고양이를 키워", None),
])
def test_only_narrow_direct_preferences_can_replace_a_subject(text, expected):
    assert preference_statement(text) == expected


def test_same_turn_correction_is_excluded_without_mutating_storage_rows():
    rows = [COFFEE, CAT]
    original = deepcopy(rows)
    assert retrieve(rows, "이제 커피 싫어해") == []
    assert rows == original
    assert retrieve(rows, "내가 커피를 싫어해?") == [COFFEE]


def test_model_fact_label_cannot_create_duplicate_preference():
    text = "나는 커피를 좋아해"
    candidates = [MemoryCandidate(kind="fact", content=text, importance=1)]
    accepted = accepted_candidates(candidates, text)
    assert len(accepted) == 1 and accepted[0]["kind"] == "preference"


def test_fact_candidate_cannot_drop_an_explicit_source_subject():
    truncated = [MemoryCandidate(kind="fact", content="부산에 살아", importance=2)]
    assert accepted_candidates(truncated, "친구는 부산에 살아.") == []

    attributed = [MemoryCandidate(kind="fact", content="친구는 부산에 살아", importance=2)]
    accepted = accepted_candidates(attributed, "친구는 부산에 살아.")
    assert len(accepted) == 1 and accepted[0]["content"] == "친구는 부산에 살아"

    implicit = [MemoryCandidate(kind="fact", content="부산에 살아", importance=2)]
    assert len(accepted_candidates(implicit, "부산에 살아.")) == 1


@pytest.mark.parametrize("text", ["친구는 커피를 싫어해", "나는 커피를 싫어해?", "나는 '커피를 싫어해'라고 말했어"])
def test_copied_substring_is_not_enough_to_overwrite_user_preference(text):
    candidates = [MemoryCandidate(kind="preference", content="커피를 싫어해", importance=3)]
    assert not accepted_candidates(candidates, text)


def test_synthetic_evaluation_fixture_uses_different_entities():
    import json
    from pathlib import Path
    data = json.loads((Path(__file__).resolve().parents[1] / "evaluation/memory-retrieval.json").read_text(encoding="utf-8"))
    for case in data["cases"]:
        actual = retrieve(data["memories"], case["message"], case["history"])
        assert [item["key"] for item in actual] == case["expected"], case["id"]
