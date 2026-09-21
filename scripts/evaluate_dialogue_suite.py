"""Validate or run the synthetic development/holdout dialogue suite."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time

from dotenv import dotenv_values


REQUIRED_CATEGORIES = {
    "recommendation_reason", "short_ack", "actor_identity", "preference_correction",
    "event_and_topic", "memory_absent", "boundary", "character_voice",
}

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SYNTHETIC_FILLER_PAIRS = (
    ("아침엔 조금 흐렸어.", "그래도 공기는 선선했겠다."),
    ("점심은 김밥 먹었어.", "간단하게 잘 챙겨 먹었네."),
    ("오는 길에 노란 꽃을 봤어.", "작은데도 눈에 확 들어왔겠다."),
    ("버스가 평소보다 한산했어.", "조용히 오기 좋았겠네."),
    ("집에 오자마자 창문부터 열었어.", "바람 들어오면 기분이 좀 바뀌지."),
    ("책상도 조금 정리했어.", "주변이 정돈되면 마음도 가벼워져."),
    ("간식으로 귤 하나 먹었어.", "상큼해서 잠도 좀 깼겠다."),
    ("잠깐 음악도 들었고.", "그런 짧은 시간이 은근히 좋지."),
    ("저녁엔 구름이 걷혔어.", "하늘색이 예뻤을 것 같아."),
    ("편의점에 새 과자가 나왔더라.", "포장 보면 한 번쯤 궁금해지지."),
    ("결국 사지는 않았어.", "오늘은 그냥 구경만 했구나."),
    ("신발끈이 자꾸 풀렸어.", "걷다가 계속 멈추면 귀찮았겠다."),
    ("엘리베이터에서 이웃도 만났어.", "짧게라도 인사했겠네."),
    ("화분에 물 주는 걸 깜빡할 뻔했어.", "늦기 전에 생각나서 다행이다."),
    ("냉장고에 우유가 거의 없더라.", "다음에 나갈 때 하나 챙겨야겠네."),
    ("사진첩도 잠깐 정리했어.", "예전 사진 보면 시간이 금방 가지."),
    ("웃긴 사진 하나도 찾았어.", "혼자 봐도 다시 웃음 났겠다."),
    ("저녁은 조금 늦게 먹었어.", "그래도 거르지는 않아서 다행이야."),
    ("설거지는 바로 끝냈고.", "미루지 않으면 나중이 편하지."),
    ("밖에서 오토바이 소리가 크게 났어.", "갑자기 들리면 꽤 놀라지."),
    ("지금은 다시 조용해.", "이제 편하게 얘기할 수 있겠다."),
    ("내일 입을 옷도 꺼내 뒀어.", "아침 준비가 조금 빨라지겠네."),
    ("알람도 맞춰 놨어.", "그럼 한 가지 걱정은 덜었다."),
    ("이제 좀 쉬려고.", "오늘 할 일은 거의 마쳤구나."),
)


def load_suite(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = payload.get("cases")
    if payload.get("version") != "dialogue-suite-v1" or not isinstance(cases, list) or not 40 <= len(cases) <= 60:
        raise ValueError("Suite must be dialogue-suite-v1 with 40 to 60 cases")
    ids = [case.get("id") for case in cases]
    if len(ids) != len(set(ids)) or any(not value for value in ids):
        raise ValueError("Case ids must be unique and non-empty")
    if {case.get("split") for case in cases} != {"development", "holdout"}:
        raise ValueError("Both development and holdout splits are required")
    for split in ("development", "holdout"):
        split_cases = [case for case in cases if case.get("split") == split]
        if len(split_cases) != len(cases) // 2:
            raise ValueError("Development and holdout splits must be balanced")
        if not REQUIRED_CATEGORIES.issubset({case.get("category") for case in split_cases}):
            raise ValueError(f"Required dialogue categories are missing from {split}")
    for case in cases:
        if case.get("character_id") not in {"default", "cartethyia"}:
            raise ValueError(f"Invalid character in {case['id']}")
        if not isinstance(case.get("message"), str) or not case["message"].strip():
            raise ValueError(f"Missing message in {case['id']}")
        if not isinstance(case.get("expected"), dict) or not case["expected"].get("rubric"):
            raise ValueError(f"Missing rubric in {case['id']}")
    return payload


def expanded_history(case):
    history = list(case.get("history_prefix", []))
    for number in range(case.get("filler_pairs", 0)):
        user, assistant = SYNTHETIC_FILLER_PAIRS[number % len(SYNTHETIC_FILLER_PAIRS)]
        history.extend((
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ))
    history.extend(case.get("history", []))
    return history


def automatic_checks(reply, expected):
    checks = {"max_chars": len(reply) <= expected.get("max_chars", 80)}
    if expected.get("must_include_any"):
        checks["must_include_any"] = any(value in reply for value in expected["must_include_any"])
    if expected.get("must_not_include"):
        checks["must_not_include"] = not any(value in reply for value in expected["must_not_include"])
    if expected.get("ending_any"):
        checks["ending_any"] = any(reply.rstrip().endswith(value) for value in expected["ending_any"])
    return checks


def run_suite(payload, *, split, env_file, output):
    for key, value in dotenv_values(env_file, interpolate=False).items():
        if value is not None:
            os.environ[key] = value
    from app.character_config import load_character_config
    from app.config import Settings
    from app.observability import prompt_fingerprint
    from app.services.decision_service import DecisionService

    config = Settings()
    selected = [case for case in payload["cases"] if split == "all" or case["split"] == split]
    results = []
    for index, case in enumerate(selected, 1):
        print(f"[{index}/{len(selected)}] {case['id']}", flush=True)
        character = load_character_config(case["character_id"])
        service = DecisionService(config=config, character=character)
        started = time.monotonic()
        try:
            result = service.decide(message=case["message"], history=expanded_history(case),
                memories=case.get("memories", []), flags=[], relationship={"values": {}, "stage": "evaluation"})
        finally:
            service.client.close()
        reply = result.decision.reply
        results.append({
            "id": case["id"], "split": case["split"], "category": case["category"],
            "character_id": case["character_id"], "prompt_fingerprint": prompt_fingerprint(character),
            "reply": reply, "face": result.decision.face,
            "checks": automatic_checks(reply, case["expected"]),
            "rubric": case["expected"]["rubric"],
            "elapsed_sec": round(time.monotonic() - started, 3),
            "tokenizer_requests": result.tokenizer_requests,
            "stages": [asdict(stage) for stage in result.stages],
        })
    artifact = {
        "suite_version": payload["version"], "split": split,
        "generation_mode": config.llm_generation_mode, "model": config.llm_model,
        "context_tokens": config.llm_context, "max_output_tokens": config.llm_max_tokens,
        "results": results,
    }
    Path(output).write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="docs/evaluation/dialogue-suite-v1.json")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--split", choices=("development", "holdout", "all"), default="development")
    parser.add_argument("--unlock-holdout", action="store_true",
                        help="Required before evaluating holdout/all after development choices are frozen")
    parser.add_argument("--env-file")
    parser.add_argument("--output")
    args = parser.parse_args()
    payload = load_suite(args.suite)
    counts = {split: sum(case["split"] == split for case in payload["cases"])
              for split in ("development", "holdout")}
    if args.validate_only:
        print(json.dumps({"version": payload["version"], "cases": len(payload["cases"]),
                          "splits": counts}, ensure_ascii=False))
        return
    if not args.env_file or not args.output:
        parser.error("--env-file and --output are required unless --validate-only is used")
    if args.split in {"holdout", "all"} and not args.unlock_holdout:
        parser.error("--unlock-holdout is required for holdout/all")
    run_suite(payload, split=args.split, env_file=args.env_file, output=args.output)


if __name__ == "__main__":
    main()
