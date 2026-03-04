from typing import Literal
from pydantic import BaseModel, Field


FaceType = Literal[
    "neutral",
    "happy",
    "sad",
    "angry",
    "crying",
    "smiling",
    "smirk",
    "shy smile",
    "blushing",
    "teary",
    "surprised",
    "confused",
    "annoyed",
    "pouting",
    "tired",
    "scared",
    "excited",
]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[ChatTurn] = Field(default_factory=list)
    comfy_on: bool = False


class ChatResponse(BaseModel):
    reply: str
    face: FaceType
    affection_delta: int
    tags: list[str]
    flags_set: list[str]
    memory_1line: str
    comfy_status: str
    image_url: str | None = None
    image_prompt: str | None = None
