"""Canonical model output. Relationship calculations belong to the server."""
from typing import Annotated, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, StrictInt, StringConstraints


def normalize_face(value):
    return {"shy smile": "shy_smile", "suprised": "surprised"}.get(value, value) if isinstance(value, str) else value


FaceType = Annotated[Literal[
    "neutral", "happy", "sad", "angry", "crying", "smiling", "smirk", "shy_smile", "blushing",
    "teary", "surprised", "confused", "annoyed", "pouting", "tired", "scared", "excited",
], BeforeValidator(normalize_face)]
InternalEmotion = Literal[
    "neutral", "happy", "sad", "angry", "anxious", "lonely", "guilty", "betrayed", "nostalgic",
    "embarrassed", "confused", "grateful", "affectionate", "curious", "excited", "tired",
]
InteractionType = Literal[
    "neutral", "compliment", "affection", "support", "self_disclosure", "shared_activity", "apology",
    "teasing", "conflict", "insult", "boundary_violation", "repair",
]
ShortString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=30)]
Intensity = Annotated[StrictInt, Field(ge=0, le=3)]


def normalize_whitespace(value):
    return " ".join(value.split()) if isinstance(value, str) else value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Interaction(StrictModel):
    type: InteractionType
    intensity: Intensity


class MemoryCandidate(StrictModel):
    kind: Literal["preference", "fact", "promise"]
    content: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
    importance: Intensity


class LLMDecision(StrictModel):
    schema_version: Annotated[StrictInt, Field(ge=1, le=1)]
    reply: Annotated[str, StringConstraints(min_length=1, max_length=80), BeforeValidator(normalize_whitespace)]
    face: FaceType
    internal_emotion: InternalEmotion
    emotion_tags: list[ShortString] = Field(min_length=1, max_length=3)
    interaction: Interaction
    memory_candidates: list[MemoryCandidate] = Field(max_length=2)
    flags_set: list[ShortString] = Field(max_length=16)
