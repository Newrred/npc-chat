"""Validated, relocatable configuration for the private portable build."""
import json
from pathlib import Path

SETTINGS = {
    "NPC_MODEL", "NPC_GENERATION_MODE", "NPC_METADATA_CONTEXT_MODE", "NPC_TOKEN_COUNT_MODE",
    "NPC_OUTPUT_CONTRACT", "NPC_JSON_MODE", "NPC_TEMP", "NPC_TOP_P", "NPC_TOP_K",
    "NPC_PRESENCE_PENALTY", "NPC_FREQUENCY_PENALTY", "NPC_REPETITION_PENALTY",
    "NPC_MAX_TOKENS", "NPC_TIMEOUT", "LLAMA_CONTEXT", "LLAMA_GPU_LAYERS",
}


def inside(root, value):
    path = Path(value)
    if path.is_absolute() or not value or ".." in path.parts:
        raise ValueError("Package path must be relative")
    resolved = (root / path).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("Package file is missing or outside package")
    return str(resolved)


def load_package(root):
    raw = json.loads((root / "desktop-package.json").read_text(encoding="utf-8"))
    if raw.get("version") != 1 or set(raw) != {"version", "model", "server", "settings"}:
        raise ValueError("Invalid package configuration")
    settings = raw["settings"]
    if not isinstance(settings, dict) or set(settings) - SETTINGS:
        raise ValueError("Unknown package setting")
    if any(not isinstance(v, str) or len(v) > 100 or "\n" in v for v in settings.values()):
        raise ValueError("Invalid package setting")
    return dict(settings, LLAMA_MODEL_PATH=inside(root, raw["model"]),
                LLAMA_SERVER_PATH=inside(root, raw["server"]), NPC_ACCESS_MODE="local",
                PYTHON_DOTENV_DISABLED="1")
