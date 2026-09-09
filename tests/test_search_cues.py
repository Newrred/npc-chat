from app.search_cues import SearchCue, validated_cues, cue_query
from tests.test_two_stage import two_stage, metadata


def test_cues_require_fitted_source_not_instructions():
    cues=[SearchCue(term='영화',quote='영화 보자'),SearchCue(term='학교',quote='학교 가자')]
    messages=[dict(role='system',content='학교 가자'),dict(role='user',content='영화 보자')]
    assert validated_cues(cues,messages)==[cues[0].model_dump()]
    assert cue_query('어딜?',validated_cues(cues,messages))=='어딜? 영화'
    assert cue_query('근데 저녁 뭐 먹지?',validated_cues(cues,messages))=='근데 저녁 뭐 먹지?'
    assert validated_cues([SearchCue(term='영화관',quote='영화 보자')],messages)==[]
    assert cue_query('어딜?',[])=='어딜?'


def test_extension_keeps_two_calls_and_canonical_decision():
    service,calls=two_stage([{'reply':'영화 보자'},metadata(search_cues=[{'term':'영화','quote':'영화 보자'}])])
    service.search_cue_experiment=True
    result=service.decide(message='뭐 할까?')
    assert len(calls)==2 and result.search_cues[0]['term']=='영화'
    assert 'search_cues' not in result.decision.model_dump()
    assert 'search_cues' not in calls[0]['response_format']['schema']['properties']
    assert 'search_cues' in calls[1]['response_format']['schema']['properties']
