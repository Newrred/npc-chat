"""Paired synthetic prompt comparison; no application DB or public visitor requests."""
import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

PENALTY_KEYS = frozenset(('llm_repetition_penalty', 'llm_presence_penalty', 'llm_frequency_penalty'))


def variant_config(config, variant):
    overrides = variant.get('sampling_overrides', {})
    if not set(overrides) <= PENALTY_KEYS:
        raise ValueError('Only penalty overrides are allowed in this comparison')
    if any(type(v) not in (int, float) or not 0 <= v <= 2 for v in overrides.values()):
        raise ValueError('Penalty overrides must be finite values in 0..2')
    return replace(config, **overrides)


class CapturingCompletions:
    def __init__(self, original):
        self.original = original
        self.seed = 0
        self.raw = []

    def create(self, **kwargs):
        response = self.original.create(**kwargs, seed=self.seed)
        self.raw.append([{'finish_reason':choice.finish_reason, 'content':choice.message.content}
                         for choice in response.choices])
        return response


def raw_reply(raw):
    try:
        return json.loads(raw[-1][0]['content']).get('reply')
    except (IndexError, TypeError, ValueError, AttributeError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--fixture', type=Path, default=ROOT / 'evaluation/identity-voice-v1.json')
    args = parser.parse_args()
    if args.output.exists() or not args.env_file.is_file():
        parser.error('Use an existing env file and a new output file')
    from dotenv import load_dotenv
    load_dotenv(args.env_file, override=True)
    from app.character_config import load_character_config
    from app.config import settings
    from app.services.decision_service import DecisionService
    if settings.llm_output_contract != 'canonical':
        parser.error('This comparison requires the canonical contract')
    fixture = json.loads(args.fixture.read_text(encoding='utf-8'))
    for variant in fixture['variants'].values():
        variant_config(settings, variant)
    base = load_character_config()
    baseline_config = replace(settings, llm_generation_mode='single_pass')
    service = DecisionService(config=baseline_config)
    original = service.client.chat.completions
    capture = CapturingCompletions(original)
    service.client.chat.completions = capture
    report = {'fixture_sha256':hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
              'settings':{key:getattr(settings,key) for key in (
                  'llm_model','llm_context','llm_max_tokens','llm_temperature','llm_top_p',
                  'llm_top_k','llm_presence_penalty','llm_frequency_penalty','llm_repetition_penalty',
                  'llm_json_mode','token_count_mode')},
              'method':'Fixed synthetic histories, rotating variant order, paired seeds; no live rollout or user DB.',
              'rows':[], 'complete':False}
    def save():
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        for repeat, seed in enumerate(fixture['seeds']):
            for index, case in enumerate(fixture['cases']):
                variants = list(fixture['variants'])
                offset = (index + repeat) % len(variants)
                for variant in variants[offset:] + variants[:offset]:
                    service.config = variant_config(baseline_config, fixture['variants'][variant])
                    service.character = replace(base,system_prompt=fixture['variants'][variant]['system_prompt'],
                        retry_user_prompt=fixture['retry_user_prompt'])
                    capture.seed = seed
                    capture.raw = []
                    row = {'case':case['id'],'variant':variant,'seed':seed,'valid':False,
                           'effective_penalties':{key:getattr(service.config,key) for key in sorted(PENALTY_KEYS)},
                           'character_prompt_sha256':hashlib.sha256(service.character.system_prompt.encode()).hexdigest()}
                    try:
                        result = service.decide(message=case['message'],history=case['history'],
                            memories=case['memories'],relationship={'values':base.initial_relationship.model_dump(),
                                                                  'stage':'getting_acquainted'})
                        row.update(valid=True,reply=result.decision.reply,raw_reply=raw_reply(capture.raw),
                            grounded_recall=result.grounded_recall,attempts=result.attempts,
                            seconds=round(result.elapsed_sec,3),prompt_tokens=result.prompt_tokens,
                            completion_tokens=result.completion_tokens,trimmed=result.context_trimmed,
                            decision=result.decision.model_dump())
                    except Exception as exc:
                        row['error_type'] = type(exc).__name__
                    row['raw_attempts'] = capture.raw
                    report['rows'].append(row)
                    save()
                    print(json.dumps({k:row[k] for k in ('case','variant','seed','valid','reply') if k in row},ensure_ascii=True),flush=True)
        report['complete'] = True
    finally:
        save()
        service.client.close()
    return 0 if all(row['valid'] for row in report['rows']) else 1


if __name__ == '__main__':
    raise SystemExit(main())
