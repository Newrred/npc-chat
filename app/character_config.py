import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from app.config import settings
from app.relationship import BASE_MATRIX, RelationshipState


CHARACTER_DIR = Path(__file__).resolve().parent / "characters"


@dataclass(frozen=True)
class CharacterConfig:
    character_id: str
    system_prompt: str
    retry_user_prompt: str
    allowed_flags: tuple[str, ...] = ()
    initial_relationship: RelationshipState = field(default_factory=RelationshipState)
    relationship_matrix: dict = field(default_factory=lambda: dict(BASE_MATRIX))
    dialogue_prompt: str | None = None
    identity_prompt: str | None = None


def _render_prompt_sections(sections: dict[str, list[str]]) -> str:
    rendered: list[str] = []
    for title, lines in sections.items():
        rendered.append(f"[{title}]")
        rendered.extend(lines)
        rendered.append(f"[{title}]")
        rendered.append("")
    return "\n".join(rendered).strip()


@lru_cache(maxsize=16)
def load_character_config(character_id: str | None = None) -> CharacterConfig:
    resolved_id = (character_id or settings.character_id or "default").strip() or "default"
    path = CHARACTER_DIR / f"{resolved_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Character config not found: {path}")

    raw = json.loads(path.read_text(encoding="utf-8"))
    if settings.llm_output_contract == "legacy":
        raw["sections"]["OUTPUT REQUIREMENT"] = raw["legacy_output_requirement"]
        raw["retry_user_prompt"] = raw["legacy_retry_user_prompt"]
    sections = raw.get("sections")
    if not isinstance(sections, dict) or not sections:
        raise ValueError(f"Character config sections are invalid: {path}")

    normalized_sections: dict[str, list[str]] = {}
    for title, lines in sections.items():
        if not isinstance(title, str) or not isinstance(lines, list) or not all(isinstance(x, str) for x in lines):
            raise ValueError(f"Character section is invalid: {title!r}")
        normalized_sections[title] = [line.strip() for line in lines if line.strip()]

    retry_user_prompt = str(raw.get("retry_user_prompt", "")).strip()
    if not retry_user_prompt:
        raise ValueError(f"Character retry_user_prompt is missing: {path}")

    allowed_flags = raw.get("allowed_flags", [])
    if not isinstance(allowed_flags, list) or not all(isinstance(flag, str) for flag in allowed_flags):
        raise ValueError("Character allowed_flags must be a list of strings")
    matrix = raw.get("relationship_matrix", BASE_MATRIX)
    if set(matrix) != set(BASE_MATRIX) or any(
        len(values) != 5 or any(type(v) is not int or not -3 <= v <= 3 for v in values)
        for values in matrix.values()
    ):
        raise ValueError("Character relationship matrix must define bounded five-stat vectors")
    return CharacterConfig(
        character_id=str(raw.get("id", resolved_id)).strip() or resolved_id,
        system_prompt=_render_prompt_sections(normalized_sections),
        retry_user_prompt=retry_user_prompt,
        allowed_flags=tuple(allowed_flags),
        initial_relationship=RelationshipState.model_validate(raw.get("initial_relationship", {})),
        relationship_matrix=matrix,
        dialogue_prompt=_render_prompt_sections({key: value for key, value in normalized_sections.items()
            if key not in {"EXAMPLES", "JSON", "OUTPUT REQUIREMENT"}}),
        identity_prompt=_render_prompt_sections({key: value for key, value in normalized_sections.items()
            if key == "IDENTITY"}),
    )
