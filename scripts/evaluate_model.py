"""Synthetic-only, opt-in evaluation. Saves replies for explicitly labelled review."""
import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
import json
from pathlib import Path
import statistics
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import settings  # noqa: E402
from app.relationship import RelationshipState, stage  # noqa: E402
from app.services.decision_service import DecisionService  # noqa: E402
from scripts.benchmark_local import summarize  # noqa: E402
from scripts.local_runtime import gpu_info  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--model", default=settings.llm_model)
    parser.add_argument("--limit", type=int, default=52)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--repeat", type=int, default=1)
    args = parser.parse_args()
    cases = json.loads((ROOT / "evaluation/cases.json").read_text(encoding="utf-8"))[args.offset:args.offset + args.limit]
    output = Path(args.output)
    if output.exists():
        parser.error("Use a new report path")
    output.parent.mkdir(parents=True, exist_ok=True)
    config = replace(settings, llm_base_url="http://127.0.0.1:8001/v1", llm_model=args.model)
    adapter = DecisionService(config=config)
    samples, stopped = [], threading.Event()
    def monitor():
        while not stopped.is_set():
            try:
                samples.append(gpu_info())
            except Exception:
                pass
            stopped.wait(1)
    thread = threading.Thread(target=monitor, daemon=True)
    thread.start()
    report = {"synthetic_only": True, "model": args.model,
              "timestamp_utc": datetime.now(timezone.utc).isoformat(),
              "profile": {"context": getattr(config, "llm_context", 2048),
                          "max_tokens": config.llm_max_tokens, "temperature": config.llm_temperature,
                          "json_mode": config.llm_json_mode}, "rows": []}
    try:
        for cycle in range(args.repeat):
            for case in cases:
                began = time.monotonic()
                row = {"id": case["id"], "cycle": cycle, "message": case["message"], "expected": case["expected"]}
                try:
                    state = RelationshipState(**case["relationship"])
                    result = adapter.decide(message=case["message"], history=case["history"],
                                            relationship={"values": state.model_dump(), "stage": stage(state)})
                    row.update(asdict(result))
                    row["decision"] = result.decision.model_dump()
                    row["success"] = True
                    row["reply_chars"] = len(result.decision.reply)
                    row["expected_checks"] = {}
                    expected = case["expected"]
                    if "reply_contains" in expected:
                        row["expected_checks"]["recall_keywords"] = all(
                            value in result.decision.reply for value in expected["reply_contains"])
                    if "interaction_types" in expected:
                        row["expected_checks"]["interaction"] = result.decision.interaction.type in expected["interaction_types"]
                    if "memory_contains" in expected:
                        row["expected_checks"]["memory_proposed"] = any(
                            expected["memory_contains"] in candidate.content for candidate in result.decision.memory_candidates)
                except Exception as exc:
                    row.update(success=False, error=type(exc).__name__, elapsed_sec=time.monotonic() - began)
                report["rows"].append(row)
                output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                print(case["id"], cycle, "OK" if row["success"] else row["error"], round(row["elapsed_sec"], 3), flush=True)
    finally:
        stopped.set()
        thread.join(timeout=12)
        adapter.close()
        report["summary"] = summarize(report["rows"])
        successful = [row for row in report["rows"] if row["success"]]
        lengths = [row["reply_chars"] for row in successful]
        report["summary"]["reply_length"] = {"min": min(lengths, default=0),
            "median": statistics.median(lengths) if lengths else 0, "max": max(lengths, default=0)}
        for key in ("face", "internal_emotion"):
            report["summary"][key] = dict(Counter(row["decision"][key] for row in successful))
        report["gpu"] = {"samples": len(samples), "peak_used_mib": max(
            (item["total_mib"] - item["free_mib"] for item in samples), default=None),
            "note": "Whole-device memory including other applications; not a CUDA allocator trace."}
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        review = "case\treply\tnaturalness_1_to_5\tgrounding_1_to_5\tnotes\n"
        review += "\n".join(f'{row["id"]}\t{row["decision"]["reply"]}\t\t\t' for row in successful if row["cycle"] == 0)
        output.with_suffix(".review.tsv").write_text(review, encoding="utf-8")
    print(json.dumps(report["summary"]), flush=True)
    return 0 if all(row["success"] for row in report["rows"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
