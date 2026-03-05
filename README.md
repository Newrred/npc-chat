<<<<<<< HEAD
# NPC Chat (Backend + Frontend Split)

This project runs NPC chat as a split setup:
- `frontend/` is a static UI (GitHub Pages)
- `app/` is a FastAPI backend
- vLLM and ComfyUI run as external services

## Architecture
- `frontend/`: static web client
- `app/`: API server (`/api/chat`, `/api/health`, `/api/image/status`)
- `vLLM`: OpenAI-compatible LLM endpoint
- `ComfyUI`: image generation endpoint

Core behavior:
- Base face images are shown immediately from frontend static files.
- Generated images are optional overlays from backend status (`queued/generated/error`).

## Project Layout
```text
app/
frontend/
  index.html
  app.js
  config.js
  styles.css
  faces/
.env.example
requirements.txt
```

## Backend Setup (Local)
1. Install dependencies
```bash
pip install -r requirements.txt
```
2. Create env file
```bash
copy .env.example .env
```
3. Configure `.env`
- LLM:
  - `NPC_BASE_URL` (example: `http://127.0.0.1:8001/v1`)
  - `NPC_API_KEY`
  - `NPC_MODEL`
- CORS:
  - `CORS_ORIGINS` (your GitHub Pages origin)
- Image policy (optional):
  - `COMFY_ENABLED`, `COMFY_CONNECT`, `COMFY_BASE_URL`
  - `COMFY_FACE_URL_TEMPLATE` (default: `/static/faces/{face_slug}.png`)
  - `COMFY_GEN_COOLDOWN_TURNS`, `COMFY_GEN_MAX_PER_MINUTE`, `COMFY_GEN_BACKOFF_SEC`
4. Run backend
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
5. Expose backend (example: cloudflared)
```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

## Frontend Setup (GitHub Pages)
Set `frontend/config.js`:
- `window.NPC_API_BASE_URL = "https://<your-backend-url>";`
- `window.NPC_FACE_ASSET_BASE_URL = "./faces";`
- `window.NPC_FACE_EXT = "png";`

Then deploy only `frontend/` to GitHub Pages.

## Face Asset Naming
Base path rule:
- `./faces/{face_slug}.png`
- `face_slug` = lowercase with spaces replaced by `_`

Required files:
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

## Hybrid Image Policy (Summary)
State flow:
- `disabled`: comfy off, use base image
- `stubbed`: comfy connect off, use cache or base
- `base`: return base image immediately
- `queued/generating`: background generation in progress
- `generated`: cached generated image reused
- `error`: keep base image with retry backoff

Runtime rules:
- Trigger generation on face change
- Optional force-regeneration for strong emotion faces
- Session rate limit, inflight limit, and per-face cooldown

## Notes
- Do not commit `.env`
- Tunnel URLs may change after restart
- Use fixed tunnel/domain for stable deployment
=======
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
>>>>>>> fc8ed695183b4e91f24b191d3a628d8cd3141e95
