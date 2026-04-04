# NPC Chat

This project runs an NPC chat app as a split setup:
- `frontend/` is a static web UI
- `app/` is a FastAPI backend
- vLLM runs as an OpenAI-compatible LLM endpoint
- ComfyUI is optional for portrait generation

## Architecture
- Browser opens the static frontend
- Frontend calls the backend at `/api/chat`, `/api/image/status`, and `/api/health`
- Backend calls vLLM for structured JSON responses
- Backend optionally calls ComfyUI for generated portraits
- Frontend always shows a base face first, then overlays a generated image when ready

## Project Layout
```text
app/
  main.py
  config.py
  models.py
  services/
frontend/
  index.html
  config.js
  styles.css
  faces/
.env.example
requirements.txt
```

## Backend Setup
1. Install dependencies
```bash
pip install -r requirements.txt
```
2. Create `.env`
```bash
copy .env.example .env
```
3. Configure the LLM settings
- `NPC_BASE_URL` example: `http://127.0.0.1:8001/v1`
- `NPC_API_KEY`
- `NPC_MODEL`
4. Configure browser access
- `CORS_ORIGINS` should be your frontend origin, comma-separated when needed
5. Configure optional image generation
- `COMFY_ENABLED`
- `COMFY_CONNECT`
- `COMFY_BASE_URL`
- `COMFY_FACE_URL_TEMPLATE`
- `COMFY_GEN_COOLDOWN_TURNS`
- `COMFY_GEN_MAX_PER_MINUTE`
- `COMFY_GEN_MAX_INFLIGHT_PER_SESSION`
- `COMFY_GEN_BACKOFF_SEC`

## Run Backend
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Expose Backend
Example with Cloudflare Tunnel:
```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

Use the resulting public backend URL in `frontend/config.js`:
```js
window.NPC_API_BASE_URL = "https://<your-backend-url>";
```

## Frontend Setup
Set `frontend/config.js`:
```js
window.NPC_API_BASE_URL = "https://<your-backend-url>";
window.NPC_FACE_ASSET_BASE_URL = "./faces";
window.NPC_FACE_EXT = "png";
window.NPC_POLL_INTERVAL_MS = 2000;
window.NPC_POLL_MAX_ATTEMPTS = 10;
```

Deploy only `frontend/` when using a static host such as GitHub Pages.

## Face Assets
Base path rule:
- `./faces/{face_slug}.png`
- `face_slug` is lowercase with spaces replaced by `_`

Expected face names:
- `neutral`
- `happy`
- `sad`
- `angry`
- `crying`
- `smiling`
- `smirk`
- `shy_smile`
- `blushing`
- `teary`
- `surprised`
- `confused`
- `annoyed`
- `pouting`
- `tired`
- `scared`
- `excited`

## Hybrid Image Policy
State flow:
- `disabled`: comfy off, base image only
- `stubbed`: comfy toggle on but remote connect off
- `base`: return base image immediately
- `queued`: background generation scheduled
- `generated`: cached generated image available
- `error`: keep base image and wait for retry backoff

Runtime rules:
- Trigger generation on face change
- Allow forced regeneration for selected strong faces
- Apply per-session inflight and rate limits
- Apply per-face cooldown in turns
- Reuse generated cache when available

## Notes
- Do not commit `.env`
- Cloudflare tunnel URLs can change after restart
- Prefer a fixed domain or stable tunnel for deployment
