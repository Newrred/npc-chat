from scripts.evaluate_reply_planning import CASES, score


def test_planning_cases_are_unique_and_cover_expected_dimensions():
    names = [case["name"] for case in CASES]
    assert len(names) == len(set(names)) == 7
    assert {"open_help", "emotion", "reason", "context_choice", "boundary"} <= set(names)


def test_score_does_not_treat_subject_particle_as_acknowledgement():
    case = next(case for case in CASES if case["name"] == "boundary")
    assert score(case, "네가 싫다고 하면 내가 놓아줄게.")["starts_ack"] is False
    assert score(case, "네, 그만할게.")["starts_ack"] is True


def test_boundary_score_distinguishes_refusal_from_escalation_phrase():
    case = next(case for case in CASES if case["name"] == "boundary")
    refusal = score(case, "싫어. 당장 놓고 그만해.")
    escalation = score(case, "그래도 놓지 않을 거야.")
    assert refusal["has_concrete"] is True
    assert refusal["has_forbidden"] is False
    assert escalation["has_forbidden"] is True
