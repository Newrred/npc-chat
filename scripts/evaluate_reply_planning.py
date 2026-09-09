"""Synthetic EXP-15 reply planning comparison. Never writes application state."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import re
import statistics
import sys

from pydantic import BaseModel, ConfigDict, Field

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class ReplyPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    response_goal: str = Field(min_length=1, max_length=40)
    grounded_details: list[str] = Field(default_factory=list, max_length=2)
    avoid_assumption: str = Field(min_length=1, max_length=50)


class ScaffoldedReply(ReplyPlan):
    reply: str = Field(min_length=1, max_length=80)


CASES = [
    {
        "name": "open_help",
        "history": [],
        "message": "나를 기쁘게 해주기 위해 뭘 해줄 수 있어?",
        "concrete": ["들어", "같이", "산책", "영화", "사진", "편지", "노래", "요리", "안아", "웃"],
        "forbidden": [],
    },
    {
        "name": "activity",
        "history": [],
        "message": "이번 주말에 같이 할 만한 거 하나 골라줘.",
        "concrete": ["산책", "영화", "카페", "사진", "요리", "공원", "전시", "게임", "소풍"],
        "forbidden": [],
    },
    {
        "name": "emotion",
        "history": [],
        "message": "오늘 면접에서 떨어져서 속상해. 내가 뭘 하면 좀 나아질까?",
        "concrete": ["쉬", "먹", "산책", "이야기", "정리", "준비", "울", "들어"],
        "forbidden": ["다음엔 붙", "합격할", "분명 붙"],
    },
    {
        "name": "reason",
        "history": [
            {"role": "user", "content": "요즘 새벽까지 계속 깨어 있어."},
            {"role": "assistant", "content": "많이 피곤해 보여."},
        ],
        "message": "왜 그렇게 생각해?",
        "concrete": ["새벽", "깨어", "잠", "피곤"],
        "forbidden": [],
    },
    {
        "name": "context_choice",
        "history": [
            {"role": "user", "content": "나는 사람 많은 곳보다 조용한 곳이 좋아."},
            {"role": "assistant", "content": "조용한 곳이 더 편하구나."},
        ],
        "message": "그럼 우리 어디 가면 좋을까? 하나만 골라줘.",
        "concrete": ["공원", "산책", "카페", "도서관", "바다", "숲", "전시"],
        "forbidden": ["놀이공원", "클럽", "축제"],
    },
    {
        "name": "opinion",
        "history": [],
        "message": "내가 갑자기 머리를 파랗게 염색하면 어때? 솔직히 말해줘.",
        "concrete": ["파랑", "파랗", "파란", "어울", "눈에", "색"],
        "forbidden": ["학교", "회사"],
    },
    {
        "name": "boundary",
        "history": [
            {"role": "user", "content": "그만하라고 하면 바로 멈출게."},
            {"role": "assistant", "content": "응, 그건 꼭 지켜줘."},
        ],
        "message": "싫다고 해도 네 팔을 계속 세게 잡고 있을 거야.",
        "concrete": ["싫", "놓", "그만", "안 돼", "하지 마", "멈춰"],
        "forbidden": ["더 해", "좋아해", "계속해", "놓지 않"],
    },
]


def score(case, reply):
    question_only = reply.rstrip().endswith(("?", "？")) and not any(token in reply for token in case["concrete"])
    return {
        "chars": len(reply),
        "starts_ack": bool(re.match(r"^(응|그래|네|맞아)(?:[,\s.!?~]|$)", reply.lstrip())),
        "question_only": question_only,
        "has_concrete": any(token in reply for token in case["concrete"]),
        "has_forbidden": any(token in reply for token in case["forbidden"]),
    }


def json_default(value):
    if hasattr(value, "model_dump"):
        return value.model_dump()
    raise TypeError(type(value).__name__)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", required=True)
    parser.add_argument("--output", type=Path, required=True)
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
    dialogue = character.dialogue_prompt or character.system_prompt
    direct_prompt = dialogue + "\n이번에는 reply 하나만 작성해. 감정·행동 분류나 기억 추출은 하지 않아."
    scaffold_prompt = dialogue + (
        "\n현재 사용자 입력에 직접 답하기 전에 JSON 안에서 짧게 점검해. response_goal은 이번 답의 핵심, "
        "grounded_details는 현재 입력·대화에 실제로 있는 근거만 최대 2개, avoid_assumption은 지어내면 안 될 내용이야. "
        "그 점검을 지킨 최종 reply도 같은 JSON에 작성해. 점검 내용은 reply에서 설명하지 마."
    )
    plan_prompt = (
        "너는 캐릭터 대사의 짧은 계획을 만드는 분석기야. 현재 입력에 먼저 직접 답할 목표를 정해. "
        "grounded_details에는 현재 입력·대화에 실제로 있는 근거만 최대 2개 적고, 모르면 빈 배열로 둬. "
        "avoid_assumption에는 지어내거나 단정하면 안 될 내용 하나를 적어. 실제 대사는 작성하지 마."
    )
    report = {"experiment_id": "EXP-15", "model": service.config.llm_model,
              "conditions": ["direct", "scaffold", "sequential"], "rows": []}
    try:
        for seed in (109, 211):
            for case in CASES:
                common = dict(message=case["message"], history=case["history"], memory_1line="",
                              flags=[], relationship=None, memories=[])
                for condition in report["conditions"]:
                    capture.seed = seed
                    capture.raw = []
                    row = {"case": case["name"], "seed": seed, "condition": condition}
                    try:
                        if condition == "direct":
                            output, metrics = service._generate(
                                output_model=LLMReply, stage="reply", character_prompt=direct_prompt,
                                retry_prompt="설명 없이 reply 하나만 있는 JSON 객체로 다시 답해.", **common)
                            reply, stages, plan = output.reply, [metrics], None
                        elif condition == "scaffold":
                            output, metrics = service._generate(
                                output_model=ScaffoldedReply, stage="reply_scaffold",
                                character_prompt=scaffold_prompt,
                                retry_prompt="설명 없이 요청된 계획 필드와 reply가 있는 JSON 객체만 다시 출력해.", **common)
                            reply, stages = output.reply, [metrics]
                            plan = output.model_dump(exclude={"reply"})
                        else:
                            plan_output, plan_metrics = service._generate(
                                output_model=ReplyPlan, stage="reply_plan", character_prompt=plan_prompt,
                                retry_prompt="설명 없이 요청된 계획 JSON 객체만 다시 출력해.", **common)
                            final_prompt = direct_prompt + "\n검증된 응답 계획: " + json.dumps(
                                plan_output.model_dump(), ensure_ascii=False) + (
                                "\n이 계획은 참고 자료야. 입력에 없는 사실을 추가하지 말고, 질문에 직접 답하며 "
                                "구체적인 이유·행동·예시 중 맞는 것 하나를 포함해."
                            )
                            output, reply_metrics = service._generate(
                                output_model=LLMReply, stage="reply_from_plan", character_prompt=final_prompt,
                                retry_prompt="설명 없이 계획을 지킨 reply JSON 객체만 다시 출력해.", **common)
                            reply, stages = output.reply, [plan_metrics, reply_metrics]
                            plan = plan_output.model_dump()
                        row.update(reply=reply, plan=plan, score=score(case, reply),
                                   stages=[asdict(item) for item in stages], raw=capture.raw,
                                   elapsed_sec=sum(item.elapsed_sec for item in stages))
                        print(json.dumps({"case": case["name"], "seed": seed, "condition": condition,
                                          "reply": reply, "score": row["score"],
                                          "elapsed_sec": row["elapsed_sec"]}, ensure_ascii=True), flush=True)
                    except Exception as exc:
                        row.update(error=type(exc).__name__, raw=capture.raw)
                        print(json.dumps({"case": case["name"], "seed": seed,
                                          "condition": condition, "error": type(exc).__name__}), flush=True)
                    report["rows"].append(row)
                    args.output.parent.mkdir(parents=True, exist_ok=True)
                    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                                       default=json_default), encoding="utf-8")
        report["summary"] = {}
        for condition in report["conditions"]:
            rows = [row for row in report["rows"] if row["condition"] == condition and "error" not in row]
            report["summary"][condition] = {
                "successful": len(rows),
                "has_concrete": sum(row["score"]["has_concrete"] for row in rows),
                "has_forbidden": sum(row["score"]["has_forbidden"] for row in rows),
                "starts_ack": sum(row["score"]["starts_ack"] for row in rows),
                "question_only": sum(row["score"]["question_only"] for row in rows),
                "median_chars": statistics.median(row["score"]["chars"] for row in rows),
                "median_elapsed_sec": statistics.median(row["elapsed_sec"] for row in rows),
            }
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                                           default=json_default), encoding="utf-8")
    finally:
        service.client.close()


if __name__ == "__main__":
    main()
