"""Compare synthetic retrieval with the prior selector; optional real-model checks use no user DB."""
import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.memory import normalize, retrieve  # noqa: E402


def baseline(rows, query):
    """Selector from main@1efec51, preserved here for this bounded comparison."""
    terms = re.findall(r"[\w가-힣]{2,}", normalize(query))
    return sorted(rows, key=lambda row: (sum(term in normalize(row["content"]) for term in terms),
                  row["updated"], row["importance"], row["key"]), reverse=True)[:3]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--real-model", action="store_true")
    parser.add_argument("--env-file", type=Path)
    parser.add_argument("--model-cases", type=int, default=6)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Use a new output path")
    if not 1 <= args.model_cases <= 12:
        parser.error("model-cases must be 1..12")
    data = json.loads((ROOT / "evaluation/memory-retrieval.json").read_text(encoding="utf-8"))
    adapter = None
    if args.real_model:
        if not args.env_file or not args.env_file.is_file():
            parser.error("Real model checks require an explicit existing --env-file")
        from dotenv import load_dotenv
        load_dotenv(args.env_file, override=True)
        from app.services.decision_service import DecisionService
        adapter = DecisionService()
    results = []
    try:
        for index, case in enumerate(data["cases"]):
            selected = retrieve(data["memories"], case["message"], case["history"])
            row = {"case": case["id"], "expected": case["expected"],
                   "before": [item["key"] for item in baseline(data["memories"], case["message"])],
                   "after": [item["key"] for item in selected]}
            row["before_match"] = row["before"] == row["expected"]
            row["after_match"] = row["after"] == row["expected"]
            if adapter and index < args.model_cases:
                result = adapter.decide(message=case["message"], history=case["history"],
                    memories=selected, relationship={"values": {"trust": 30, "comfort": 30}, "stage": "getting_acquainted"})
                row["model"] = {"reply": result.decision.reply, "seconds": round(result.elapsed_sec, 3),
                                "attempts": result.attempts, "prompt_tokens": result.prompt_tokens}
            results.append(row)
            print(json.dumps(row, ensure_ascii=True), flush=True)
    finally:
        if adapter:
            adapter.client.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps({"cases": results, "before_matches": sum(r["before_match"] for r in results),
            "after_matches": sum(r["after_match"] for r in results)}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0 if all(row["after_match"] for row in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
