from app.reply_quality import (compact_repetitive_history, is_short_ack, recent_reply_similarity,
                               repeated_reply_count, reply_guidance, reply_similarity)
from tests.test_two_stage import metadata, two_stage


def pairs(replies):
    return [item for n, reply in enumerate(replies)
            for item in ({"role": "user", "content": f"말 {n}"}, {"role": "assistant", "content": reply})]


def test_repetition_compaction_preserves_pairs_latest_and_source():
    history = pairs(["처음 답변", "응, 살짝만 더 해줘.", "응, 조금만 더 해줘.",
                     "응, 살짝만 해줘.", "새로운 답변"])
    compacted, removed = compact_repetitive_history(history)
    assert removed == 2 and len(compacted) % 2 == 0
    assert compacted[-2:] == history[-2:]
    assert history[3]["content"] == "응, 살짝만 더 해줘."
    assert all(compacted[i]["role"] == ("user" if i % 2 == 0 else "assistant")
               for i in range(len(compacted)))


def test_invalid_history_shape_is_not_rewritten():
    history = [{"role": "assistant", "content": "응"}]
    assert compact_repetitive_history(history) == (history, 0)


def test_guidance_distinguishes_ack_question_request_emotion_and_default():
    assert is_short_ack("ㅇㅇ") and "짧은 확인" in reply_guidance("ㅇㅇ")
    assert "직접 답" in reply_guidance("나를 위해 뭘 해줄 수 있어?")
    assert "수락하거나 거절" in reply_guidance("같이 영화 보자")
    assert "구체적인 원인" in reply_guidance("오늘 너무 속상해")
    assert "맞장구만" in reply_guidance("오늘 학교 다녀왔어")


def test_similarity_finds_near_duplicate_without_equating_distinct_topics():
    assert reply_similarity("응, 살짝만 더 해줘.", "응, 조금만 더 해줘.") >= 0.70
    assert reply_similarity("오늘은 영화 보자.", "오늘은 책 읽자.") < 0.70
    history = pairs(["응, 살짝만 더 해줘", "응, 조금만 더 해줘"])
    assert recent_reply_similarity("응, 조금만 더 해줘", history) >= 0.70
    assert repeated_reply_count("응, 조금만 더 해줘", history) == 2


def test_duplicate_candidate_retries_once_and_metadata_sees_better_reply():
    history = pairs(["응, 살짝만 더 해줘.", "응, 조금만 더 해줘."])
    service, calls = two_stage([
        {"reply": "응, 조금만 더 해줘."},
        {"reply": "싫어. 그만하고 다른 얘기하자."},
        metadata(),
    ])
    try:
        result = service.decide(message="그럼 계속할게", history=history)
        assert result.decision.reply == "싫어. 그만하고 다른 얘기하자."
        assert [stage.stage for stage in result.stages] == ["reply", "reply_quality_retry", "metadata"]
        assert len(calls) == 3 and result.attempts == 3
        assert "싫어. 그만하고 다른 얘기하자." in calls[-1]["messages"][0]["content"]
    finally:
        service.client.close()


def test_reply_stage_compacts_repetition_but_metadata_keeps_original_history():
    history = pairs(["응, 살짝만 더 해줘.", "응, 조금만 더 해줘.", "응, 살짝만 해줘."])
    service, calls = two_stage([{"reply": "그 얘기는 이제 그만하자."}, metadata()])
    try:
        service.decide(message="다른 얘기하자", history=history)
        assert len(calls[0]["messages"][1:-1]) == 4
        assert len(calls[1]["messages"][1:-1]) == 6
        assert "반복 대사 1쌍을 생략" in calls[0]["messages"][0]["content"]
        assert "이번 답변 방식" not in calls[0]["messages"][0]["content"]
        assert len(history) == 6
    finally:
        service.client.close()


def test_short_ack_does_not_trigger_quality_retry():
    service, calls = two_stage([{"reply": "응, 알았어."}, metadata()])
    try:
        result = service.decide(message="응", history=pairs(["응, 알았어."]))
        assert len(calls) == 2 and [stage.stage for stage in result.stages] == ["reply", "metadata"]
    finally:
        service.client.close()
