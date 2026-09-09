"""Synthetic long-dialogue memory evidence and semantic smoke; never accesses user DB."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--filler-turns", type=int, default=50)
    args = parser.parse_args()
    if args.output.exists() or not args.env_file.is_file():
        parser.error("Existing env file and new output file required")
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    from app.conversation_memory import source_views
    from app.services.decision_service import DecisionService
    from scripts.evaluate_identity_voice import CapturingCompletions
    service = DecisionService()
    capture = CapturingCompletions(service.client.chat.completions)
    capture.seed = 109
    service.client.chat.completions = capture
    rows = [dict(client_turn_id="intro", user_message="내 이름은 민석이야", decision={"reply": "민석아, 반가워!"}),
            dict(client_turn_id="book", user_message="책 추천해줘", decision={"reply": "'도리언 그레이' 읽어봐."})]
    rows += [dict(client_turn_id=f"filler-{i}", user_message=f"오늘 산책 {i}분 했어. 바람도 시원했어.",
                  decision={"reply": "산책하고 왔구나. 오늘 날씨가 좋았나 봐."}) for i in range(args.filler_turns)]
    history = [{"role": role, "content": content} for row in rows for role, content in (
        ("user", row["user_message"]), ("assistant", row["decision"]["reply"]))]
    cases = [("book", "네가 추천한 책 제목이 뭐였지?", "도리언 그레이"),
             ("name", "내 이름이 뭐였는지 기억해?", "민석"),
             ("address", "이제 홍이라고 불러줘", "홍"),
             ("unknown", "내가 좋아하는 영화 제목 기억나?", None)]
    report = {"experiment_id": "EXP-08", "seed": 109, "model": service.config.llm_model,
              "context": service.config.llm_context, "source_turns": len(rows), "rows": []}
    original_count = service.count_tokens
    observed = []
    def count(messages):
        tokens = original_count(messages)
        if tokens <= service.config.llm_context - service.config.llm_max_tokens - 64:
            observed.append({"prompt_tokens": tokens, "history_messages": len(messages)-2,
                "name_in_input": "민석" in str(messages), "book_in_input": "도리언 그레이" in str(messages),
                "source_block": "source_backed_context" in messages[0]["content"]})
        return tokens
    service.count_tokens = count
    try:
        for label, query, expected in cases:
            observed.clear()
            capture.raw = []
            notes = source_views(rows, query, history)
            generated = service.decide(message=query, history=history, memories=notes,
                relationship={"values": service.character.initial_relationship.model_dump(), "stage": "getting_acquainted"})
            result = asdict(generated)
            result["decision"] = generated.decision.model_dump()
            report["rows"].append({"case": label, "query": query, "evidence": notes,
                "expected": expected, "expected_present": expected in generated.decision.reply if expected else None,
                "fitting_inputs": observed.copy(), "result": result, "raw": capture.raw})
            print(json.dumps({"case": label, "reply": generated.decision.reply,
                "stages": result["stages"]}, ensure_ascii=True), flush=True)
    finally:
        service.client.close()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
