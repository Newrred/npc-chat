from itertools import product

import pytest
from pydantic import ValidationError

from app.decision import Interaction
from app.relationship import BASE_MATRIX, DIMENSIONS, RelationshipState, calculate, from_legacy


@pytest.mark.parametrize("kind,intensity", product(BASE_MATRIX, range(4)))
def test_every_base_vector(kind, intensity):
    state = RelationshipState(**dict.fromkeys(DIMENSIONS, 50))
    result = calculate(state, Interaction(type=kind, intensity=intensity))
    expected = [max(-3, min(3, value * intensity)) for value in BASE_MATRIX[kind]]
    assert list(result.delta.model_dump().values()) == expected
    assert list(result.values.model_dump().values()) == [50 + v for v in expected]
    assert result.rule_version == "1.0"


@pytest.mark.parametrize("kind,intensity,total", product(BASE_MATRIX, range(4), (0, 1, 99, 100)))
def test_bounds_actual_delta_and_determinism(kind, intensity, total):
    state = RelationshipState(**dict.fromkeys(DIMENSIONS, total))
    interaction = Interaction(type=kind, intensity=intensity)
    first = calculate(state, interaction)
    assert first == calculate(state, interaction)
    for key, value in first.values.model_dump().items():
        assert 0 <= value <= 100
        assert getattr(first.delta, key) == value - total
        assert -3 <= getattr(first.delta, key) <= 3
    if intensity == 0:
        assert first.values == state


def test_teasing_repetition_and_irritation():
    interaction = Interaction(type="teasing", intensity=2)
    result = calculate(RelationshipState(comfort=39), interaction)
    assert result.delta.comfort == 0 and result.delta.irritation == 1
    assert "TEASING_LOW_COMFORT" in result.reason_codes
    assert calculate(RelationshipState(comfort=40), interaction).delta.comfort == 2
    positive = Interaction(type="affection", intensity=2)
    result = calculate(RelationshipState(irritation=70), positive, [positive])
    assert result.delta.affection == result.delta.comfort == 0
    assert result.delta.interest == 1
    assert {"REPEATED_POSITIVE", "HIGH_IRRITATION"} <= set(result.reason_codes)
    neutral = Interaction(type="neutral", intensity=0)
    assert calculate(RelationshipState(), positive, [positive, neutral, neutral, neutral]).delta.affection == 2


def test_repetition_zero_and_negative_are_not_attenuated():
    support = Interaction(type="support", intensity=1)
    assert calculate(RelationshipState(), support, [support]).delta.model_dump() == dict.fromkeys(DIMENSIONS, 0)
    insult = Interaction(type="insult", intensity=2)
    assert calculate(RelationshipState(trust=50), insult, [insult]).delta.trust == -2


def test_legacy_defaults_and_strict_validation():
    defaults = RelationshipState(trust=22, comfort=44)
    assert from_legacy(900, defaults) == RelationshipState(affection=100, trust=22, comfort=44)
    assert from_legacy(-20, defaults).affection == 0
    for invalid in (-1, 101, True, "20"):
        with pytest.raises(ValidationError):
            RelationshipState(affection=invalid)
