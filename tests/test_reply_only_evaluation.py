from dataclasses import replace
import json
from pathlib import Path

import pytest

from app.config import Settings
from scripts.evaluate_reply_only import parse_reply, simple_request


@pytest.mark.parametrize('raw,mode', [('','plain'), (' '*3,'plain'), ('x'*81,'plain'),
    ('{"reply":"a"}','plain'), ('```a```','plain'), ('{"reply":12}','reply_json'),
    ('{"reply":"a","face":"happy"}','reply_json'), ('{}','reply_json')])
def test_simple_invalid_output_is_not_silently_repaired(raw,mode):
    with pytest.raises(ValueError):
        parse_reply(raw,mode)


def test_reply_modes_keep_dialogue_and_reject_extra_fields():
    assert parse_reply(' 응, 알았어. ','plain') == '응, 알았어.'
    assert parse_reply('{"reply":"응, 알았어."}','reply_json') == '응, 알았어.'


def test_simple_request_keeps_context_and_sampling_but_only_json_mode_has_schema():
    config=replace(Settings(),llm_context=4096,llm_max_tokens=256,llm_backend='llama_cpp')
    case={'message':'왜?', 'history':[{'role':'user','content':'잠을 못 잤어'},
        {'role':'assistant','content':'피곤하겠다'}], 'memories':[]}
    before=json.dumps(case)
    requests=[]
    for mode in ('reply_json','plain'):
        request,tokens,trimmed=simple_request(config,'너는 유이야.',case,{},mode,lambda _:100)
        requests.append(request)
        assert [m['role'] for m in request['messages']]==['system','user','assistant','user']
        assert request['messages'][-1]['content']=='왜?'
        assert request['messages'][1:3]==case['history']
        assert request['max_tokens']==256 and tokens==100 and not trimmed
        assert request['extra_body']['repeat_penalty']==config.llm_repetition_penalty
        assert request['presence_penalty']==config.llm_presence_penalty
        assert request['extra_body']['chat_template_kwargs']=={'enable_thinking':False}
    assert set(requests[0]['response_format']['schema']['properties'])=={'reply'}
    assert 'response_format' not in requests[1]
    assert json.dumps(case)==before


def test_ablation_snapshots_have_true_history_control_and_shared_no_example_baseline():
    root=Path(__file__).resolve().parents[1]
    examples=json.loads((root/'evaluation/example-boundary-v1.json').read_text(encoding='utf-8'))
    reply=json.loads((root/'evaluation/reply-only-v1.json').read_text(encoding='utf-8'))
    assert reply['canonical_prompt']==examples['variants']['C_no_examples']['system_prompt']
    assert reply['cases']==examples['cases']
    assert '[EXAMPLES]' not in reply['canonical_prompt']
    assert '[JSON]' not in reply['dialogue_prompt']
    cases={c['id']:c for c in reply['cases']}
    assert not cases['interview']['history']
    assert '시험' in cases['real_exam']['history'][0]['content']
