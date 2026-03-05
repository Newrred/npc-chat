# Hybrid Image Policy

## Goal
- Keep chat latency low by returning a base portrait immediately.
- Generate images only when needed, then reuse cached results.
- Keep behavior deterministic across the fixed `face` enum.

## Policy JSON Schema
```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "NpcImageHybridPolicy",
  "type": "object",
  "additionalProperties": false,
  "required": [
    "character_id",
    "style_version",
    "base_face_url_template",
    "cooldown_turns",
    "max_gen_per_minute",
    "max_inflight_per_session",
    "backoff_sec",
    "force_regen_faces"
  ],
  "properties": {
    "character_id": { "type": "string", "minLength": 1 },
    "style_version": { "type": "string", "minLength": 1 },
    "base_face_url_template": { "type": "string", "minLength": 1 },
    "cooldown_turns": { "type": "integer", "minimum": 0 },
    "max_gen_per_minute": { "type": "integer", "minimum": 1 },
    "max_inflight_per_session": { "type": "integer", "minimum": 1 },
    "backoff_sec": { "type": "integer", "minimum": 0 },
    "force_regen_faces": {
      "type": "array",
      "items": { "type": "string", "minLength": 1 },
      "uniqueItems": true
    }
  }
}
```

## State Machine (Text)
```text
[disabled]
  condition: comfy_on=false OR COMFY_ENABLED=false
  action: return base image only

[stubbed]
  condition: comfy_on=true, COMFY_ENABLED=true, COMFY_CONNECT=false
  action: return generated cache if exists else base image

[base]
  condition: comfy_on=true, COMFY_ENABLED=true, COMFY_CONNECT=true
  action: return base image immediately
  transitions:
    -> queued (if policy allows generation)
    -> generated (if cache hit)

[queued]
  action: background job scheduled
  transitions:
    -> generating (worker picked job)
    -> error (job start failure)

[generating]
  action: call Comfy /generate
  transitions:
    -> generated (image_url returned)
    -> error (timeout/network/invalid payload)

[generated]
  action: store image in cache (key: character_id:style_version:face)
  action: return cached image on next requests

[error]
  action: keep base image, set retry backoff
  transitions:
    -> queued (after backoff and policy pass)
```

## Runtime Rules
- Trigger generation when `face` changes.
- Allow forced re-generation for selected strong faces.
- Rate limit per session per minute.
- Keep max inflight generation per session.
- Enforce cooldown per face in turns.
- Use base portrait while queued, generating, or error.

## Base Asset Naming
- Place face images under `app/static/faces/`.
- Default URL template is `/static/faces/{face_slug}.png`.
- Example file names:
  - `neutral.png`
  - `happy.png`
  - `sad.png`
  - `angry.png`
  - `crying.png`
  - `smiling.png`
  - `smirk.png`
  - `shy_smile.png`
  - `blushing.png`
  - `teary.png`
  - `surprised.png`
  - `confused.png`
  - `annoyed.png`
  - `pouting.png`
  - `tired.png`
  - `scared.png`
  - `excited.png`
