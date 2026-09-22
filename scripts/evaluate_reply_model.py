"""Synthetic EXP-16 direct-reply model comparison. Never writes application state."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.evaluate_reply_planning import CASES, score  # noqa: E402


def json_default(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--label", required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output file")

    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    from app.character_config import load_character_config
    from app.decision import LLMReply
    from app.services.decision_service import DecisionService
    from scripts.evaluate_identity_voice import CapturingCompletions

    service = DecisionService()
    character = load_character_config()
    capture = CapturingCompletions(service.client.chat.completions)
    service.client.chat.completions = capture
    prompt = (character.dialogue_prompt or character.system_prompt) + (
        "\n이번에는 reply 하나만 작성해. 감정·행동 분류나 기억 추출은 하지 않아."
    )
    report = {"experiment_id": "EXP-16", "label": args.label,
              "model_alias": service.config.llm_model, "rows": []}
    try:
        for seed in (109, 211):
            for case in CASES:
                capture.seed = seed
                capture.raw = []
                row = {"case": case["name"], "seed": seed}
                try:
                    output, metrics = service._generate(
                        output_model=LLMReply, stage="reply", character_prompt=prompt,
                        retry_prompt="설명 없이 reply 하나만 있는 JSON 객체로 다시 답해.",
                        message=case["message"], history=case["history"], memory_1line="",
                        flags=[], relationship=None, memories=[])
                    row.update(reply=output.reply, score=score(case, output.reply),
                               stages=[asdict(metrics)], raw=capture.raw,
                               elapsed_sec=metrics.elapsed_sec)
                    print(json.dumps({"case": case["name"], "seed": seed, "reply": output.reply,
                                      "score": row["score"], "elapsed_sec": row["elapsed_sec"]},
                                     ensure_ascii=True), flush=True)
                except Exception as exc:
                    row.update(error=type(exc).__name__, raw=capture.raw)
                    print(json.dumps({"case": case["name"], "seed": seed,
                                      "error": type(exc).__name__}), flush=True)
                report["rows"].append(row)
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                                   default=json_default), encoding="utf-8")
    finally:
        service.close()


if __name__ == "__main__":
    main()
