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
2. Publish `frontend/` directory to GitHub Pages.

## Notes
- Keep `.env` out of git.
- Quick Tunnel URL can change each restart.
- For stability, use named Cloudflare Tunnel + fixed domain later.
