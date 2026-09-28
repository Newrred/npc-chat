"""Sequential, synthetic development-only model comparison; no application DB.

Start one model with the existing launcher, then run this script against loopback.
The caller owns model lifecycle. Outputs contain synthetic dialogue only.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.evaluate_dialogue_suite import expanded_history, load_suite  # noqa: E402


def file_hash(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def request_hash(messages):
    return hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument("--model-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    from app.character_config import load_character_config
    from app.config import Settings
    from app.interaction_policy import reward_guard
    from app.relationship import RelationshipState, calculate
    from app.services.decision_service import DecisionService
    config = Settings()
    config.llm_base_url = "http://127.0.0.1:8001/v1"
    config.llm_model = args.model
    config.llm_generation_mode = "two_stage"
    config.metadata_context_mode = "full"
    config.llm_context = 4096
    config.llm_max_tokens = 256
    config.token_count_mode = "llama_cpp"
    suite_path = ROOT / "docs/evaluation/dialogue-suite-v1.json"
    cases = [c for c in load_suite(suite_path)["cases"] if c["split"] == "development"]
    artifact = dict(model=args.model, model_file=Path(args.model_file).name,
                    model_sha256=file_hash(args.model_file), seed=args.seed,
                    suite_sha256=file_hash(suite_path), context=4096, output_tokens=256,
                    generation_mode="two_stage", metadata_context_mode="full",
                    sampler={k: getattr(config, k) for k in (
                        "llm_temperature", "llm_top_p", "llm_top_k", "llm_repetition_penalty",
                        "llm_presence_penalty", "llm_frequency_penalty")},
                    source_hashes={p: file_hash(ROOT / p) for p in (
                        "app/services/decision_service.py", "app/prompt_context.py",
                        "app/characters/default.json", "app/interaction_policy.py")},
                    scope="Synthetic development24, injected memories, no DB; seed fixed, not deterministic guarantee",
                    results=[])
    for index, case in enumerate(cases, 1):
        print(f"{index}/{len(cases)} {case['id']}", flush=True)
        service = DecisionService(config=config, character=load_character_config(case["character_id"]))
        create = service.client.chat.completions.create
        calls = []

        def seeded_create(**kwargs):
            kwargs["seed"] = args.seed
            response = create(**kwargs)
            calls.append(dict(messages_sha256=request_hash(kwargs["messages"]),
                              raw_content=response.choices[0].message.content,
                              finish_reason=response.choices[0].finish_reason))
            return response

        service.client.chat.completions.create = seeded_create
        started = time.monotonic()
        row = dict(id=case["id"], category=case["category"], message=case["message"], calls=calls)
        try:
            result = service.decide(message=case["message"], history=expanded_history(case),
                                    memories=case.get("memories", []), flags=[],
                                    relationship={"values": {}, "stage": "evaluation"})
            effective, reason = reward_guard(case["message"], result.decision.interaction)
            row.update(decision=result.decision.model_dump(), grounded_recall=result.grounded_recall,
                       effective_interaction=effective.model_dump(), guard_reason=reason,
                       raw_delta=calculate(RelationshipState(), result.decision.interaction).delta.model_dump(),
                       effective_delta=calculate(RelationshipState(), effective).delta.model_dump(),
                       stages=[asdict(s) for s in result.stages])
        except Exception as exc:
            row.update(error=type(exc).__name__, stages=[asdict(s) for s in getattr(exc, "stages", ())])
        finally:
            service.close()
        row["elapsed_sec"] = round(time.monotonic() - started, 3)
        artifact["results"].append(row)
        Path(args.output).write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Completed", len(artifact["results"]), flush=True)


if __name__ == "__main__":
    main()
