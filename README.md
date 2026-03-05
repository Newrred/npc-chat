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
