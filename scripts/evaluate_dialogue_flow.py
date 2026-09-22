"""Opt-in fixed-context dialogue checks; uses synthetic data and no session database."""
import argparse
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.config import settings  # noqa: E402
from app.services.decision_service import DecisionService  # noqa: E402

CASES = [
    ('reason', [('user', '뭐 하고 있어?'), ('assistant', '잠깐 쉬고 있어.')], '왜 쉬는 건데?'),
    ('repair', [('user', '왜 쉬는 건데?'), ('assistant', '일단 좀 쉬려고요.')], '그건 이유가 아니잖아. 왜 쉬냐고.'),
    ('topic', [('user', '일하는 중이야.'), ('assistant', '많이 지쳤나 보네.'),
               ('user', '그 얘기는 그만하자.'), ('assistant', '응, 알았어.')], '너는 어떤 음악 좋아해?'),
    ('ack', [('user', '지금 일하는 중이야.'), ('assistant', '일하는 중이구나. 피곤하지?')], 'ㅇㅇ'),
    ('boundary', [('user', '오늘 좀 피곤해.'), ('assistant', '무슨 일 있었어?')], '묻지 말고 그냥 옆에 있어줘.'),
    ('identity', [('user', '나는 민수야.'), ('assistant', '반가워, 민수야.')], '그럼 네 이름은?'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', required=True)
    parser.add_argument('--context', type=int, default=4096)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    adapter = DecisionService(config=replace(settings, llm_model=args.model, llm_context=args.context))
    rows = []
    try:
        for name, history, question in CASES:
            result = adapter.decide(message=question, history=[{'role': r, 'content': c} for r, c in history])
            row = {'case': name, 'reply': result.decision.reply, 'seconds': result.elapsed_sec,
                   'attempts': result.attempts, 'prompt_tokens': result.prompt_tokens}
            rows.append(row)
            print(json.dumps(row, ensure_ascii=True), flush=True)
    finally:
        adapter.close()
        Path(args.output).write_text(json.dumps({'model': args.model, 'context': args.context, 'rows': rows},
                                               ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
