"""Opt-in synthetic multi-turn repetition check; never reads or writes user sessions."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.decision_service import DecisionService  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows = []
    service = DecisionService()
    try:
        for scenario in ('fresh', 'repeated_history'):
            history = [
                {'role': 'user', 'content': '지금 일하는 중이야.'},
                {'role': 'assistant', 'content': '일하는 중이구나. 피곤하지?'},
            ]
            if scenario == 'repeated_history':
                history += [
                    {'role': 'user', 'content': 'ㅇ'},
                    {'role': 'assistant', 'content': '일하는 중이구나. 피곤하지?'},
                ] * 2
            for message in ('ㅇ', 'ㅇㅇ', 'ㅇㅇㅇㅇ', '응이라고', '니 이름뭔데'):
                result = service.decide(message=message, history=history[-12:])
                row = asdict(result)
                row['decision'] = result.decision.model_dump()
                row.update(scenario=scenario, message=message,
                           exact_repeat=result.decision.reply == history[-1]['content'])
                rows.append(row)
                history.extend([{'role': 'user', 'content': message},
                                {'role': 'assistant', 'content': result.decision.reply}])
    finally:
        service.client.close()
    report = {'rows': rows, 'exact_repeats': sum(row['exact_repeat'] for row in rows),
              'cases': len(rows), 'context': service.config.llm_context}
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))


if __name__ == '__main__':
    main()
