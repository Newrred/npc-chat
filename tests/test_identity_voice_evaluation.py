import json
from pathlib import Path
from types import SimpleNamespace
import pytest

from scripts.evaluate_identity_voice import CapturingCompletions, raw_reply, variant_config


def test_capture_preserves_model_reply_and_seed_without_mutating_request():
    calls = []
    response = SimpleNamespace(choices=[SimpleNamespace(finish_reason='stop',
        message=SimpleNamespace(content='{"reply":"original"}'))])
    def create(**kwargs):
        calls.append(kwargs)
        return response
    capture = CapturingCompletions(SimpleNamespace(create=create))
    capture.seed = 37
    request = {'messages':[{'role':'user','content':'synthetic'}]}
    assert capture.create(**request) is response
    assert calls[0]['seed'] == 37 and 'seed' not in request
    assert raw_reply(capture.raw) == 'original'
    response.choices[0].message.content = '{"reply":"changed later"}'
    assert raw_reply(capture.raw) == 'original'


def test_raw_reply_keeps_invalid_generation_as_missing():
    assert raw_reply([]) is None
    assert raw_reply([[{'content':'not json'}]]) is None
    assert raw_reply([[{'content':'[]'}]]) is None


def test_snapshot_baseline_matches_original_character_and_variants_keep_examples_separate():
    from app.character_config import _render_prompt_sections
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root/'evaluation/identity-voice-v1.json').read_text(encoding='utf-8'))
    a,b,c = [data['variants'][key] for key in 'ABC']
    assert a['system_prompt'] == _render_prompt_sections(a['sections'])
    assert a['sections']['EXAMPLES'] == b['sections']['EXAMPLES']
    assert b['sections']['IDENTITY'] == c['sections']['IDENTITY']
    assert b['sections']['CHARACTER'] == c['sections']['CHARACTER']
    assert b['sections']['JSON'] == c['sections']['JSON']
    assert a['sections']['EXAMPLES'] != c['sections']['EXAMPLES']
    assert len({case['id'] for case in data['cases']}) == len(data['cases'])


def test_penalty_variant_does_not_mutate_baseline_or_other_settings():
    from app.config import Settings
    baseline = Settings()
    changed = variant_config(baseline, {'sampling_overrides':{'llm_repetition_penalty':1.0}})
    assert changed is not baseline
    assert changed.llm_repetition_penalty == 1.0
    assert changed.llm_presence_penalty == baseline.llm_presence_penalty
    assert changed.llm_frequency_penalty == baseline.llm_frequency_penalty
    assert changed.llm_model == baseline.llm_model
    assert changed.llm_context == baseline.llm_context


@pytest.mark.parametrize('overrides', [
    {'llm_model':'different'}, {'llm_temperature':0.1}, {'llm_repetition_penalty':float('nan')},
    {'llm_repetition_penalty':float('inf')}, {'llm_repetition_penalty':True},
    {'llm_repetition_penalty':-1}, {'llm_repetition_penalty':'1.0'},
])
def test_invalid_comparison_overrides_rejected(overrides):
    from app.config import Settings
    with pytest.raises(ValueError):
        variant_config(Settings(), {'sampling_overrides':overrides})


def test_sampling_fixture_freezes_prompt_and_isolates_repeat():
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root/'evaluation/sampling-v1.json').read_text(encoding='utf-8'))
    variants = data['variants']
    assert len({v['system_prompt'] for v in variants.values()}) == 1
    current = variants['A_current']['sampling_overrides']
    for key in ('B_repeat_off', 'C_repeat_high'):
        other = variants[key]['sampling_overrides']
        assert [name for name in current if current[name] != other[name]] == ['llm_repetition_penalty']
