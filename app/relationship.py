"""Pure, deterministic five-stat rules. No model-provided score is accepted."""
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.decision import Interaction

RULE_VERSION = "1.0"
DIMENSIONS = ("affection", "trust", "comfort", "interest", "irritation")
Score = Annotated[StrictInt, Field(ge=0, le=100)]
Delta = Annotated[StrictInt, Field(ge=-3, le=3)]
BASE_MATRIX = {
    "neutral": (0, 0, 0, 0, 0), "compliment": (1, 0, 0, 1, 0),
    "affection": (1, 0, 1, 1, 0), "support": (0, 1, 1, 0, -1),
    "self_disclosure": (0, 1, 0, 1, 0), "shared_activity": (0, 0, 1, 1, 0),
    "apology": (0, 1, 0, 0, -1), "teasing": (0, 0, 1, 0, 0),
    "conflict": (0, -1, -1, 0, 1), "insult": (-1, -1, 0, 0, 2),
    "boundary_violation": (-1, -2, -2, 0, 2), "repair": (0, 1, 1, 0, -2),
}
POSITIVE = frozenset(key for key, values in BASE_MATRIX.items() if any(v > 0 for v in values[:4]))


class RelationshipState(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    affection: Score = 0
    trust: Score = 30
    comfort: Score = 30
    interest: Score = 30
    irritation: Score = 0


class RelationshipDelta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    affection: Delta = 0
    trust: Delta = 0
    comfort: Delta = 0
    interest: Delta = 0
    irritation: Delta = 0


class RelationshipResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    values: RelationshipState
    delta: RelationshipDelta
    reason_codes: list[str]
    rule_version: str = RULE_VERSION


def from_legacy(total: int, defaults: RelationshipState) -> RelationshipState:
    return RelationshipState(**(defaults.model_dump() | {"affection": max(0, min(100, int(total)))}))


def stage(state: RelationshipState) -> str:
    if state.irritation >= 70:
        return "strained"
    if state.trust >= 60 and state.comfort >= 60:
        return "close"
    return "getting_acquainted"


def calculate(state: RelationshipState, interaction: Interaction, recent=(), matrix=None) -> RelationshipResult:
    matrix = BASE_MATRIX if matrix is None else matrix
    intensity = interaction.intensity
    reasons = ["BASE_" + interaction.type.upper(), f"INTENSITY_{intensity}"]
    if interaction.type in POSITIVE and any(
        previous.type == interaction.type and previous.intensity > 0 for previous in list(recent)[-3:]
    ) and intensity > 0:
        intensity -= 1
        reasons.append("REPEATED_POSITIVE")
    vector = {key: max(-3, min(3, value * intensity))
              for key, value in zip(DIMENSIONS, matrix[interaction.type], strict=True)}
    if intensity > 0:
        if interaction.type == "teasing" and state.comfort < 40:
            vector["comfort"] = 0
            vector["irritation"] = min(3, vector["irritation"] + 1)
            reasons.append("TEASING_LOW_COMFORT")
        if state.irritation >= 70:
            changed = False
            for key in ("affection", "comfort"):
                if vector[key] > 0:
                    vector[key] -= 1
                    changed = True
            if changed:
                reasons.append("HIGH_IRRITATION")
    before = state.model_dump()
    after = {}
    for key in DIMENSIONS:
        proposed = before[key] + vector[key]
        after[key] = max(0, min(100, proposed))
        if after[key] != proposed:
            reasons.append("CLAMP_" + key.upper())
    actual_delta = {key: after[key] - before[key] for key in DIMENSIONS}
    return RelationshipResult(values=RelationshipState(**after), delta=RelationshipDelta(**actual_delta),
                              reason_codes=reasons)
