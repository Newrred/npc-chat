"""Opt-in synthetic same-model two-stage verification with stage timings and raw output."""
import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from scripts.evaluate_identity_voice import CapturingCompletions  # noqa: E402


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() or not args.env_file.is_file():
        parser.error('Use an existing env file and a new output path')
    from dotenv import load_dotenv
    load_dotenv(args.env_file,override=True)
    from app.config import settings
    from app.services.decision_service import DecisionService
    config=replace(settings,llm_generation_mode='two_stage')
    service=DecisionService(config=config)
    capture=CapturingCompletions(service.client.chat.completions)
    capture.seed=109
    service.client.chat.completions=capture
    fixtures=json.loads((ROOT/'evaluation/reply-only-holdout-v1.json').read_text(encoding='utf-8'))
    cases=[case for case in fixtures['cases'] if case['id'] in ('holdout_cause','holdout_identity','holdout_apology')]
    cases.append({'id':'grounded_recall','message':'내가 녹차 좋아했지?','history':[],
                  'memories':[{'kind':'preference','content':'이제 녹차 싫어해'}]})
    report={'experiment_id':'EXP-07','parent':'EXP-06','model':config.llm_model,'context':config.llm_context,
            'max_tokens_per_stage':config.llm_max_tokens,'seed':109,'cases':cases,'rows':[],'complete':False}
    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        for case in cases:
            capture.raw=[]
            row={'case':case['id'],'success':False}
            try:
                result=service.decide(message=case['message'],history=case['history'],memories=case['memories'],
                    relationship={'values':service.character.initial_relationship.model_dump(),'stage':'getting_acquainted'})
                row.update(asdict(result))
                row['decision']=result.decision.model_dump()
                row['success']=True
            except Exception as exc:
                row['error_type']=type(exc).__name__
            row['raw_attempts']=capture.raw
            report['rows'].append(row)
            save()
            print(json.dumps({k:row[k] for k in ('case','success','decision','stages') if k in row},ensure_ascii=True),flush=True)
        report['complete']=True
    finally:
        save()
        service.client.close()
    return 0 if all(row['success'] for row in report['rows']) else 1


if __name__=='__main__':
    raise SystemExit(main())
