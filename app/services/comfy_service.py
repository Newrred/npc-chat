from typing import Any

import httpx

from app.config import settings


def build_face_prompt(face: str, tags: list[str], reply: str) -> str:
    tags_part = ", ".join(tags[:2]) if tags else "neutral"
    return f"anime portrait, npc face, expression: {face}, mood tags: {tags_part}, dialogue mood: {reply[:80]}"


class ComfyService:
    async def maybe_generate(
        self,
        *,
        comfy_on: bool,
        face: str,
        tags: list[str],
        reply: str,
    ) -> dict[str, Any]:
        prompt = build_face_prompt(face, tags, reply)

        if not comfy_on or not settings.comfy_enabled:
            return {
                "comfy_status": "disabled",
                "image_url": None,
                "image_prompt": prompt,
            }

        # Toggle is on but remote connection is intentionally disabled.
        if not settings.comfy_connect:
            return {
                "comfy_status": "stubbed",
                "image_url": None,
                "image_prompt": prompt,
            }

        # Minimal placeholder protocol for future Comfy API wiring.
        payload = {
            "prompt": prompt,
            "meta": {"source": "npc-web"},
        }

        try:
            async with httpx.AsyncClient(timeout=settings.comfy_timeout_sec) as client:
                resp = await client.post(f"{settings.comfy_base_url}/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
            return {
                "comfy_status": "generated",
                "image_url": data.get("image_url"),
                "image_prompt": prompt,
            }
        except Exception:
            return {
                "comfy_status": "error",
                "image_url": None,
                "image_prompt": prompt,
            }
