from dataclasses import replace
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.character_config import load_character_config
from app.decision import LLMDecision, LLMReply, LLMMetadata
from app.errors import ChatError
from app.services.decision_service import DecisionService, LLMOutputError, LLMTransportError
from tests.test_decision import service, valid


def metadata(**changes):
    data = valid()
    data.pop('reply')
    data.update(changes)
    return data


def two_stage(responses, mode='schema'):
    adapter, calls = service(responses, mode)
    adapter.config = replace(adapter.config, llm_generation_mode='two_stage', llm_context=4096)
    return adapter, calls


def test_provider_metrics_allowlist_llama_timings_and_cached_tokens():
    response = SimpleNamespace(
        model_extra={"timings": {"cache_n": 12, "prompt_ms": 3.5, "private_note": "hidden"}},
        usage=SimpleNamespace(prompt_tokens_details=SimpleNamespace(cached_tokens=9)),
    )
    assert DecisionService._provider_metrics(response) == {
        "cache_n": 12, "prompt_ms": 3.5, "cached_tokens": 9,
    }


def test_projected_contracts_preserve_validation_and_cannot_rewrite_reply():
    assert LLMReply(reply='  응\n 알았어. ').reply == '응 알았어.'
    with pytest.raises(ValidationError):
        LLMReply(reply='x'*81)
    with pytest.raises(ValidationError):
        LLMMetadata(**valid())
    output = LLMMetadata(**metadata())
    assert output.face == 'shy_smile'
    assert LLMDecision(reply='응', **output.model_dump()).reply == '응'
    canonical = LLMDecision.model_json_schema()
    subset = LLMMetadata.model_json_schema()
    for key in LLMMetadata.model_fields:
        assert subset['properties'][key] == canonical['properties'][key]


def test_benchmark_does_not_count_normal_second_stage_as_retry():
    from scripts.benchmark_local import summarize
    result = summarize([
        {'success':True,'attempts':2,'elapsed_sec':1,'stages':[{'attempts':1},{'attempts':1}]},
        {'success':True,'attempts':3,'elapsed_sec':2,'stages':[{'attempts':1},{'attempts':2}]},
    ])
    assert result['first_pass_rate']==0.5 and result['retry_recoveries']==1


def test_two_requests_same_model_fixed_reply_and_metrics():
    adapter, calls = two_stage([{'reply':'응, 반가워.'}, metadata()])
    adapter.character = load_character_config('default')
    try:
        result = adapter.decide(message='안녕', history=[{'role':'user','content':'어제 왔어'},
            {'role':'assistant','content':'반가워'}])
        assert len(calls) == 2
        assert set(calls[0]['response_format']['schema']['properties']) == {'reply'}
        assert 'reply' not in calls[1]['response_format']['schema']['properties']
        assert '[EXAMPLES]' not in calls[0]['messages'][0]['content']
        assert 'memory_candidates' not in calls[0]['messages'][0]['content']
        assert 'assistant_reply_to_analyze' in calls[1]['messages'][0]['content']
        assert '응, 반가워.' in calls[1]['messages'][0]['content']
        for call in calls:
            assert call['messages'][-1] == {'role':'user','content':'안녕'}
            assert call['messages'][1]['content'] == '어제 왔어'
        for key in ('model','max_tokens','temperature','top_p','top_k','repeat_penalty',
                    'presence_penalty','frequency_penalty','chat_template_kwargs'):
            assert calls[0][key] == calls[1][key]
        assert result.decision.reply == '응, 반가워.'
        assert [m.stage for m in result.stages] == ['reply','metadata']
        assert result.attempts == 2 and result.completion_tokens == 200
        assert result.prompt_tokens == sum(m.prompt_tokens for m in result.stages)
        assert all(m.prepare_sec >= 0 and m.inference_sec >= 0 for m in result.stages)
    finally:
        adapter.client.close()


def test_metadata_sees_grounded_final_reply_instead_of_generated_guess():
    adapter, calls = two_stage([{'reply':'커피 좋아하지?'}, metadata()])
    try:
        result = adapter.decide(message='내가 커피 좋아했지?',
            memories=[{'kind':'preference','content':'이제 커피 싫어해'}])
        assert result.grounded_recall
        assert result.decision.reply in calls[1]['messages'][0]['content']
        assert '커피 좋아하지?' not in str(calls[1]['messages'])
    finally:
        adapter.client.close()


@pytest.mark.parametrize(('character_id', 'expected'), [
    ('default', "네가 '나는 커피를 싫어해'라고 했어."),
    ('cartethyia', "전에 '나는 커피를 싫어해'라고 했어요."),
])
def test_grounded_recall_uses_character_voice_and_metadata_sees_same_reply(character_id, expected):
    adapter, calls = two_stage([{'reply':'커피를 좋아한다고 했어요.'}, metadata()])
    adapter.character = load_character_config(character_id)
    try:
        result = adapter.decide(message='커피는 내가 좋아하는 거였어?',
            memories=[{'kind':'preference','content':'나는 커피를 싫어해.'}])
        assert result.decision.reply == expected and len(expected) <= 80
        assert expected in calls[1]['messages'][0]['content']
        assert '커피를 좋아한다고 했어요.' not in str(calls[1]['messages'])
    finally:
        adapter.client.close()


def test_metadata_retry_never_regenerates_reply_or_accepts_replacement():
    adapter, calls = two_stage([{'reply':'원래 대사'}, metadata(reply='바꾸려는 대사'), metadata(flags_set=['known','bad'])])
    try:
        result = adapter.decide(message='안녕')
        assert len(calls) == 3 and result.decision.reply == '원래 대사'
        assert [m.attempts for m in result.stages] == [1,2]
        assert result.parse_failures == 1 and result.decision.flags_set == ['known']
        assert all('assistant_reply_to_analyze' in c['messages'][0]['content'] for c in calls[1:])
        assert all('원래 대사' in c['messages'][0]['content'] for c in calls[1:])
    finally:
        adapter.client.close()


@pytest.mark.parametrize('responses,error,count', [
    ([('{}','stop')]*3, LLMOutputError, 3),
    ([{'reply':'대사'}, 503, 503, 503], LLMTransportError, 4),
    ([{'reply':'대사'}, ('{}','stop'), ('{}','stop'), ('{}','stop')], LLMOutputError, 4),
])
def test_failed_stage_has_bounded_calls_and_no_private_logging(responses,error,count,caplog):
    adapter, calls = two_stage(responses)
    try:
        with pytest.raises(error) as raised:
            adapter.decide(message='PRIVATE_SENTINEL')
        assert len(calls) == count
        assert raised.value.stages and raised.value.stages[-1].elapsed_sec >= 0
        assert 'PRIVATE_SENTINEL' not in caplog.text
    finally:
        adapter.client.close()


def test_metadata_budget_protects_current_input_and_frozen_reply():
    adapter, calls = two_stage([{'reply':'이 대사는 잘리면 안 돼'}])
    seen = []
    def count(messages):
        seen.append(messages)
        return 10000 if 'assistant_reply_to_analyze' in messages[0]['content'] else 100
    adapter.count_tokens = count
    try:
        with pytest.raises(ChatError, match='문맥 한도'):
            adapter.decide(message='현재 메시지 보존', history=[{'role':'user','content':'과거'},
                {'role':'assistant','content':'과거 답변'}])
        assert len(calls) == 1
        for messages in seen[1:]:
            assert messages[-1]['content'] == '현재 메시지 보존'
            assert '이 대사는 잘리면 안 돼' in messages[0]['content']
    finally:
        adapter.client.close()


def test_shared_deadline_prevents_metadata_request(monkeypatch):
    import app.services.decision_service as module
    clock = [0.0]
    adapter, calls = two_stage([{'reply':'안녕'}])
    adapter.config = replace(adapter.config, llm_timeout_sec=1)
    adapter.count_tokens = lambda _: 100
    original = adapter.client.chat.completions.create
    def delayed(**kwargs):
        result = original(**kwargs)
        clock[0] = 4.0
        return result
    adapter.client.chat.completions.create = delayed
    monkeypatch.setattr(module.time,'monotonic',lambda:clock[0])
    try:
        with pytest.raises(LLMTransportError,match='deadline'):
            adapter.decide(message='안녕')
        assert len(calls) == 1
    finally:
        adapter.client.close()


def test_two_stage_api_duplicate_commits_once_and_rejects_assistant_memory(backend):
    client, store, _ = backend
    ids = client.post('/api/session',json={}).json()
    adapter, calls = two_stage([{'reply':'나는 고양이를 키워'}, metadata(
        memory_candidates=[{'kind':'fact','content':'나는 고양이를 키워','importance':2}])])
    client.app.state.llm_service = adapter
    payload = {**ids,'client_turn_id':'two-stage','message':'안녕'}
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _:client.post('/api/chat',json=payload),range(2)))
        assert all(r.status_code == 200 for r in responses)
        assert responses[0].json() == responses[1].json()
        assert len(calls) == 2
        state = store.load(ids['profile_id'],'default')
        assert state.turn_count == 1 and len(state.history) == 2
        assert not store.recall(ids['profile_id'],'default','고양이')
    finally:
        adapter.client.close()


@pytest.mark.parametrize('failure', ['metadata','database'])
def test_two_stage_api_failure_preserves_everything(backend,failure):
    client, store, _ = backend
    ids = client.post('/api/session',json={}).json()
    before = store.load(ids['profile_id'],'default')
    responses = [{'reply':'그렇구나'}, *( [503]*3 if failure=='metadata' else [metadata()])]
    adapter, calls = two_stage(responses)
    client.app.state.llm_service = adapter
    if failure=='database':
        def fail(point):
            if point=='after_memory':
                raise sqlite3.OperationalError('synthetic')
        store.failpoint = fail
    try:
        response = client.post('/api/chat',json={**ids,'client_turn_id':'failure','message':'나는 녹차를 좋아해'})
        assert response.status_code == 503
        assert store.load(ids['profile_id'],'default') == before
        assert not store.recall(ids['profile_id'],'default','녹차')
        assert len(calls) == (4 if failure=='metadata' else 2)
    finally:
        adapter.client.close()


def test_two_stage_lost_response_replays_without_either_model_call(backend):
    client, store, _ = backend
    ids = client.post('/api/session',json={}).json()
    adapter, calls = two_stage([{'reply':'안녕'},metadata()])
    client.app.state.llm_service = adapter
    def fail(point):
        if point=='after_commit':
            raise sqlite3.OperationalError('synthetic')
    store.failpoint = fail
    payload={**ids,'client_turn_id':'lost-two-stage','message':'안녕'}
    try:
        assert client.post('/api/chat',json=payload).status_code == 503
        store.failpoint = None
        assert client.post('/api/chat',json=payload).status_code == 200
        assert len(calls)==2 and store.load(ids['profile_id'],'default').turn_count==1
    finally:
        adapter.client.close()


def test_cancel_during_metadata_never_commits(tmp_path):
    import asyncio
    import threading
    import httpx
    from app.main import create_app
    from app.repository import SQLiteRepository
    async def run():
        started, release = threading.Event(), threading.Event()
        adapter, calls = two_stage([{'reply':'안녕'},metadata()])
        original = adapter.client.chat.completions.create
        def blocked_metadata(**kwargs):
            if len(calls)==1:
                started.set()
                assert release.wait(5)
            return original(**kwargs)
        adapter.client.chat.completions.create = blocked_metadata
        repo = SQLiteRepository(tmp_path/'cancel.sqlite3')
        metric_records = []
        metric_sink = SimpleNamespace(emit=metric_records.append, close=lambda: None)
        application = create_app(repository=repo,llm_service=adapter,metrics_sink=metric_sink)
        try:
            async with application.router.lifespan_context(application):
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application),base_url='http://test') as client:
                    ids=(await client.post('/api/session',json={})).json()
                    before=repo.load(ids['profile_id'],'default')
                    request=asyncio.create_task(client.post('/api/chat',json={**ids,'message':'안녕','client_turn_id':'cancel'}))
                    await asyncio.to_thread(started.wait,3)
                    assert started.is_set() and len(calls)==1
                    request.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await request
                    release.set()
                    await application.state.coordinator.close()
                    assert repo.load(ids['profile_id'],'default')==before
                    turn_metric = next(row for row in metric_records if row['event'] == 'turn_complete')
                    assert turn_metric['outcome'] == 'cancelled'
        finally:
            release.set()
            adapter.client.close()
    asyncio.run(run())
