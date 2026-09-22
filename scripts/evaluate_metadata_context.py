"""Compare full and compact metadata context against the same frozen synthetic replies."""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import time

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_dialogue_suite import expanded_history, load_suite  # noqa: E402


def run(*, suite_path, baseline_path, env_file, output):
    for key, value in dotenv_values(env_file, interpolate=False).items():
        if value is not None:
            os.environ[key] = value
    from app.character_config import load_character_config
    from app.config import Settings
    from app.decision import MemoryCandidate
    from app.memory import accepted_candidates
    from app.services.decision_service import DecisionService

    suite = load_suite(suite_path)
    cases = {case["id"]: case for case in suite["cases"] if case["split"] == "development"}
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    frozen = {row["id"]: row["reply"] for row in baseline["results"]}
    if set(cases) != set(frozen):
        raise ValueError("Baseline result ids must exactly match the development split")
    config = Settings()
    services = {character_id: DecisionService(config=config,
        character=load_character_config(character_id)) for character_id in {c["character_id"] for c in cases.values()}}
    results = []
    try:
        for index, case in enumerate(cases.values(), 1):
            order = ("full", "compact") if index % 2 else ("compact", "full")
            for mode in order:
                print(f"[{index}/{len(cases)}] {case['id']} {mode}", flush=True)
                service = services[case["character_id"]]
                started = time.monotonic()
                metadata, metrics, _ = service.analyze_metadata(
                    message=case["message"], assistant_reply=frozen[case["id"]],
                    history=expanded_history(case), memory_1line="", flags=[],
                    relationship={"values": {}, "stage": "evaluation"},
                    memories=case.get("memories", []), context_mode=mode)
                candidates = [MemoryCandidate.model_validate(item)
                              for item in metadata.model_dump()["memory_candidates"]]
                accepted = accepted_candidates(candidates, case["message"])
                results.append({
                    "id": case["id"], "category": case["category"], "mode": mode,
                    "order": order.index(mode) + 1, "character_id": case["character_id"],
                    "frozen_reply": frozen[case["id"]], "metadata": metadata.model_dump(),
                    "accepted_candidates": accepted,
                    "elapsed_sec": round(time.monotonic() - started, 3),
                    "stage": asdict(metrics),
                })
    finally:
        for service in services.values():
            service.client.close()
    artifact = {
        "experiment": "EXP-21", "suite_version": suite["version"],
        "baseline": str(Path(baseline_path).name), "model": config.llm_model,
        "context_tokens": config.llm_context, "max_output_tokens": config.llm_max_tokens,
        "results": results,
    }
    Path(output).write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return artifact


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", default="docs/evaluation/dialogue-suite-v1.json")
    parser.add_argument("--baseline", default="docs/evaluation/dialogue-suite-development-baseline-v1.json")
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(suite_path=args.suite, baseline_path=args.baseline, env_file=args.env_file, output=args.output)


if __name__ == "__main__":
    main()
