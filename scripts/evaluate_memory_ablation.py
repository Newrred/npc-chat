"""Synthetic history versus actual memory retrieval ablation; no user database."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Output must be new')
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    from app.conversation_memory import source_views
    from app.services.decision_service import DecisionService
    from scripts.evaluate_identity_voice import CapturingCompletions
    service = DecisionService()
    capture = CapturingCompletions(service.client.chat.completions)
    service.client.chat.completions = capture
    rows = [dict(client_turn_id='movie', user_message='영화 추천해줘.', decision={'reply':"영화는 '월터의 상상은 현실이 된다' 어때?"}),
            dict(client_turn_id='time', user_message='오늘 저녁 8시에 보러갈까', decision={'reply':'좋아! 8시에 만나요.'})]
    def history(source):
        return [dict(role=role, content=text) for row in source for role,text in (
            ('user',row['user_message']),('assistant',row['decision']['reply']))]
    recent = [dict(role='user',content='오늘 바람이 시원하네.'),dict(role='assistant',content='산책하기 좋겠다.')]
    report = {'experiment_id':'EXP-09','model':service.config.llm_model,'source_rows':rows,
              'context':service.config.llm_context,'rows':[]}
    try:
        for seed in (109,211):
            for case, query, tail in [('explicit','우리 보기로 한 영화 제목이 뭐였지?',recent),
                    ('implicit','어딜?',recent+[dict(role='user',content='어라 벌써 8시가 다 되어가네'),dict(role='assistant',content='응, 빨리 가자!')])]:
                for variant in ('history_only','retrieval_only','neither'):
                    supplied = history(rows)+tail if variant=='history_only' else tail
                    notes = source_views(rows,query,tail) if variant=='retrieval_only' else []
                    capture.seed=seed
                    capture.raw=[]
                    observed=[]
                    original_count=service.count_tokens
                    def count(messages):
                        tokens=original_count(messages)
                        if tokens<=service.config.llm_context-service.config.llm_max_tokens-64:
                            observed.append({'messages':messages,'tokens':tokens})
                        return tokens
                    service.count_tokens=count
                    try:
                        result=service.decide(message=query,history=supplied,memories=notes,
                            relationship={'values':service.character.initial_relationship.model_dump(),'stage':'getting_acquainted'})
                        output=asdict(result)
                        output['decision']=result.decision.model_dump()
                        record=dict(seed=seed,case=case,variant=variant,query=query,memories=notes,
                                    inputs=observed,result=output,raw=capture.raw)
                        print(json.dumps(dict(seed=seed,case=case,variant=variant,memories=len(notes),reply=result.decision.reply),ensure_ascii=True),flush=True)
                    except Exception as error:
                        record=dict(seed=seed,case=case,variant=variant,error=type(error).__name__,inputs=observed)
                    finally:
                        service.count_tokens=original_count
                    report['rows'].append(record)
                    args.output.parent.mkdir(parents=True,exist_ok=True)
                    args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:
        service.close()


if __name__=='__main__':
    main()
