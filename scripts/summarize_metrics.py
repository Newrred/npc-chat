"""Summarize private-content-free turn JSONL metrics."""
import argparse
from collections import Counter
import json
import math
from pathlib import Path


TIMING_FIELDS = (
    "queue_wait_ms", "identity_ms", "ownership_check_ms", "replay_lookup_ms",
    "repository_load_ms", "recall_ms", "reply_prepare_ms", "reply_infer_ms",
    "metadata_prepare_ms", "metadata_infer_ms", "image_ms", "commit_ms", "total_ms",
)


def percentile(values, fraction):
    ordered = sorted(values)
    if not ordered:
        return None
    return ordered[max(0, math.ceil(len(ordered) * fraction) - 1)]


def summarize(records):
    turns = [row for row in records if row.get("event") == "turn_complete"]
    timings = {}
    for field in TIMING_FIELDS:
        values = [row[field] for row in turns
                  if isinstance(row.get(field), (int, float)) and not isinstance(row.get(field), bool)]
        if values:
            timings[field] = {"count": len(values), "p50": percentile(values, .50),
                              "p95": percentile(values, .95), "max": max(values)}
    return {
        "turns": len(turns),
        "outcomes": dict(sorted(Counter(row.get("outcome", "unknown") for row in turns).items())),
        "errors": dict(sorted(Counter(row["error_code"] for row in turns if row.get("error_code")).items())),
        "replayed": sum(bool(row.get("replayed")) for row in turns),
        "timings_ms": timings,
    }


def load(paths):
    records = []
    for path in paths:
        with Path(path).open(encoding="utf-8") as handle:
            for number, line in enumerate(handle, 1):
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSONL: {path}:{number}") from exc
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--output")
    args = parser.parse_args()
    result = summarize(load(args.paths))
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
