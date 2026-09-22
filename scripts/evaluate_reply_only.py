"""Synthetic canonical / reply JSON / plain reply ablation, isolated from the web app."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.evaluate_identity_voice import CapturingCompletions, raw_reply  # noqa: E402


class ReplyOnly(BaseModel):
    model_config = ConfigDict(extra='forbid')
    reply: Annotated[str, StringConstraints(strict=True, strip_whitespace=True, min_length=1, max_length=80)]


def parse_reply(raw, mode):
    if mode == 'reply_json':
        return ReplyOnly.model_validate_json(raw).reply
    if mode != 'plain':
        raise ValueError('Unsupported simple mode')
    if raw.strip().startswith(('{', '```', '<think>')):
        raise ValueError('Expected plain dialogue, not structured output')
    return ReplyOnly(reply=raw).reply


def simple_request(config, dialogue, case, relationship, mode, counter):
    from app.prompt_context import build_messages, compact_schema
    if mode not in ('reply_json', 'plain'):
        raise ValueError('Unsupported simple mode')
    schema = ReplyOnly.model_json_schema()
    if mode == 'reply_json':
        system = 'Output one JSON object matching this schema:\n' + json.dumps(compact_schema(schema), separators=(',', ':'))
        system += '\n' + dialogue + '\n이번에는 reply 하나만 작성해. 감정·행동 분류나 기억 추출은 하지 않아.'
    else:
        system = dialogue + '\n이번에는 대사만 1~80글자로 출력해. JSON, 역할 이름, 설명을 붙이지 마. 감정·행동 분류나 기억 추출은 하지 않아.'
    messages, tokens, trimmed = build_messages(system=system,message=case['message'],history=case['history'],
        summary='',memories=case['memories'],relationship=relationship,flags=[],count=counter,
        budget=config.llm_context-config.llm_max_tokens-64)
    body = {'chat_template_kwargs':{'enable_thinking':False},'top_k':config.llm_top_k,
            'repeat_penalty' if config.llm_backend == 'llama_cpp' else 'repetition_penalty':config.llm_repetition_penalty}
    request = dict(model=config.llm_model,messages=messages,max_tokens=config.llm_max_tokens,
        temperature=config.llm_temperature,top_p=config.llm_top_p,presence_penalty=config.llm_presence_penalty,
        frequency_penalty=config.llm_frequency_penalty,extra_body=body)
    if mode == 'reply_json':
        request['response_format']={'type':'json_object','schema':schema}
    return request, tokens, trimmed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--fixture',type=Path,default=ROOT/'evaluation/reply-only-v1.json')
    args = parser.parse_args()
    if args.output.exists() or not args.env_file.is_file():
        parser.error('Use an existing env file and a new output path')
    from dotenv import load_dotenv
    load_dotenv(args.env_file,override=True)
    from app.config import settings
    from app.services.decision_service import DecisionService
    if settings.llm_backend != 'llama_cpp' or settings.llm_json_mode != 'schema':
        parser.error('This controlled experiment requires llama_cpp/schema')
    data = json.loads(args.fixture.read_text(encoding='utf-8'))
    service = DecisionService(config=replace(settings, llm_generation_mode='single_pass'))
    service.character = replace(service.character,system_prompt=data['canonical_prompt'],retry_user_prompt=data['retry_user_prompt'])
    capture = CapturingCompletions(service.client.chat.completions)
    service.client.chat.completions = capture
    relationship={'values':service.character.initial_relationship.model_dump(),'stage':'getting_acquainted'}
    report={'experiment_id':'EXP-06','parent':'EXP-05',
        'fixture_sha256':hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
        'settings':{key:getattr(settings,key) for key in ('llm_model','llm_context','llm_max_tokens','llm_temperature',
            'llm_top_p','llm_top_k','llm_presence_penalty','llm_frequency_penalty','llm_repetition_penalty','token_count_mode')},
        'rows':[],'complete':False}
    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        for repeat,seed in enumerate(data['seeds']):
            for index,case in enumerate(data['cases']):
                modes=['canonical','reply_json','plain']
                offset=(index+repeat)%3
                for mode in modes[offset:]+modes[:offset]:
                    capture.seed=seed
                    capture.raw=[]
                    row={'case':case['id'],'variant':mode,'seed':seed,'valid':False}
                    start=time.monotonic()
                    try:
                        if mode=='canonical':
                            result=service.decide(message=case['message'],history=case['history'],memories=case['memories'],relationship=relationship)
                            row.update(valid=True,reply=result.decision.reply,raw_reply=raw_reply(capture.raw),
                                attempts=result.attempts,prompt_tokens=result.prompt_tokens,trimmed=result.context_trimmed,
                                completion_tokens=result.completion_tokens,grounded_recall=result.grounded_recall)
                        else:
                            request,tokens,trimmed=simple_request(settings,data['dialogue_prompt'],case,relationship,mode,service.count_tokens)
                            row.update(prompt_tokens=tokens,trimmed=trimmed,attempts=1,grounded_recall=False)
                            response=capture.create(**request)
                            row['completion_tokens']=getattr(response.usage,'completion_tokens',None)
                            choice=response.choices[0]
                            if choice.finish_reason!='stop':
                                raise ValueError('Incomplete generation')
                            reply=parse_reply(choice.message.content or '',mode)
                            row.update(valid=True,reply=reply,raw_reply=reply)
                    except Exception as exc:
                        row['error_type']=type(exc).__name__
                    row['seconds']=round(time.monotonic()-start,3)
                    row['raw_attempts']=capture.raw
                    report['rows'].append(row)
                    save()
                    print(json.dumps({k:row[k] for k in ('case','variant','seed','valid','reply') if k in row},ensure_ascii=True),flush=True)
        report['complete']=True
    finally:
        save()
        service.close()
    return 0 if all(row['valid'] for row in report['rows']) else 1


if __name__=='__main__':
    raise SystemExit(main())
