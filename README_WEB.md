# Backend + Frontend Split Deployment

## Structure
- `app/`: FastAPI backend API only (`/api/chat`, `/api/health`)
- `frontend/`: static client for GitHub Pages

## Backend (local PC)
1. `pip install -r requirements.txt`
2. `copy .env.example .env`
3. Set `.env`:
   - `NPC_BASE_URL` (local vLLM URL, e.g. `http://127.0.0.1:8001/v1`)
   - `NPC_API_KEY`, `NPC_MODEL`
   - `CORS_ORIGINS` (your GitHub Pages origin)
4. Run backend:
   - `uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload`
5. Expose backend via tunnel:
   - `cloudflared tunnel --url http://127.0.0.1:8000`

## Frontend (GitHub Pages)
1. In `frontend/config.js`, set:
   - `window.NPC_API_BASE_URL = "https://<your-backend-tunnel>";`
   - `window.NPC_FACE_ASSET_BASE_URL = "./faces";`
   - `window.NPC_FACE_EXT = "png";`
2. Put base face images in `frontend/faces/` with these names:
   - `neutral.png`, `happy.png`, `sad.png`, `angry.png`, `crying.png`, `smiling.png`,
     `smirk.png`, `shy_smile.png`, `blushing.png`, `teary.png`, `surprised.png`,
     `confused.png`, `annoyed.png`, `pouting.png`, `tired.png`, `scared.png`, `excited.png`
3. Generated image polling uses backend endpoint `/api/image/status`, while base faces are always loaded from frontend static files.
4. Publish `frontend/` directory to GitHub Pages.

## Notes
- Keep `.env` out of git.
- Quick Tunnel URL can change each restart.
- For stability, use named Cloudflare Tunnel + fixed domain later.
