"""Local admin signed, per-request experiments; never change the shared character."""
import base64
from dataclasses import replace
import hashlib
import hmac
import json
from pathlib import Path
import secrets
import time

from pydantic import BaseModel, Field


class PromptDraft(BaseModel):
    identity: str = Field(min_length=1, max_length=1500)
    dialogue: str = Field(min_length=1, max_length=3500)


def key_path(database):
    return Path(str(database) + ".inspector.key")


def issue(database, draft, body):
    path = key_path(database)
    try:
        with path.open("xb") as f:
            f.write(secrets.token_bytes(32))
    except FileExistsError:
        pass
    payload = {"draft": draft.model_dump(), "expires": time.time() + 600,
               "binding": binding(body)}
    encoded = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode()).decode()
    signature = hmac.new(path.read_bytes(), encoded.encode(), hashlib.sha256).hexdigest()
    return encoded + "." + signature


def binding(body):
    return {k: body.get(k) for k in ("profile_id", "session_id", "client_turn_id", "message")}


def verify(database, token, body):
    try:
        if len(token) > 45000:
            raise ValueError()
        encoded, signature = token.rsplit(".", 1)
        expected = hmac.new(key_path(database).read_bytes(), encoded.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError()
        payload = json.loads(base64.urlsafe_b64decode(encoded))
        if payload["expires"] < time.time() or payload["binding"] != binding(body):
            raise ValueError()
        return PromptDraft.model_validate(payload["draft"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise ValueError("Invalid local prompt experiment") from exc


def character_with_draft(character, draft):
    return replace(character, identity_prompt=draft.identity,
                   dialogue_prompt=draft.identity + "\n" + draft.dialogue)


def revision(draft):
    return hashlib.sha256(draft.model_dump_json().encode()).hexdigest()[:12]
