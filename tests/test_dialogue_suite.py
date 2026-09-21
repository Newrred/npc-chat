import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.evaluate_dialogue_suite import automatic_checks, expanded_history, load_suite


SUITE = Path(__file__).parents[1] / "docs" / "evaluation" / "dialogue-suite-v1.json"


def test_dialogue_suite_has_balanced_unseen_split_and_required_categories():
    payload = load_suite(SUITE)
    cases = payload["cases"]
    assert len(cases) == 48
    assert sum(case["split"] == "development" for case in cases) == 24
    assert sum(case["split"] == "holdout" for case in cases) == 24
    assert all("PRIVATE" not in json.dumps(case) for case in cases)
    long_cases = [case for case in cases if case.get("filler_pairs", 0) >= 20]
    assert len(long_cases) >= 2 and all(len(expanded_history(case)) >= 40 for case in long_cases)
    assert all(len({turn["content"] for turn in expanded_history(case)}) >= 20 for case in long_cases)
    assert all(set(case["expected"]["rubric"]) == {
        "format", "actor_accuracy", "grounding", "substance", "naturalness", "character_consistency"
    } for case in cases)


def test_dialogue_suite_checks_are_separate_from_human_rubric():
    expected = {"max_chars": 10, "must_include_any": ["우동"],
                "must_not_include": ["뭐든"], "ending_any": ["요."]}
    assert all(automatic_checks("우동 좋아요.", expected).values())
    assert not all(automatic_checks("뭐든 좋아요.", expected).values())


def test_dialogue_suite_rejects_duplicate_ids(tmp_path):
    payload = json.loads(SUITE.read_text(encoding="utf-8"))
    payload["cases"][1]["id"] = payload["cases"][0]["id"]
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError, match="unique"):
        load_suite(path)


def test_dialogue_suite_cli_validates_from_repository_root():
    completed = subprocess.run(
        [sys.executable, "scripts/evaluate_dialogue_suite.py", "--validate-only"],
        cwd=SUITE.parents[2], capture_output=True, text=True, check=True,
    )
    assert '"cases": 48' in completed.stdout
