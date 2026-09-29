"""Private desktop app factory; never used by the public entry point."""
import os
import secrets

from fastapi.responses import JSONResponse


def create_desktop_app():
    from app.main import create_app
    token = os.environ.get("NPC_DESKTOP_TOKEN", "")
    if len(token) < 32:
        raise RuntimeError("Desktop token required")
    if os.environ.get("NPC_DESKTOP_TEST") == "1":
        from tests.fakes import FakeLLM

        async def probe():
            pass
        application = create_app(llm_service=FakeLLM(), llm_probe=probe)
    else:
        application = create_app()

    @application.middleware("http")
    async def desktop_boundary(request, call_next):
        supplied = request.headers.get("x-npc-desktop", "")
        # Health probes use Authorization; renderer receives no token in JS.
        supplied = supplied or request.headers.get("authorization", "").removeprefix("Bearer ")
        if (request.headers.get("host") != "127.0.0.1:8003"
                or request.headers.get("origin") not in (None, "http://127.0.0.1:8003")
                or not secrets.compare_digest(supplied.encode(), token.encode())):
            return JSONResponse({"error": "DESKTOP_ACCESS_DENIED"}, status_code=403)
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-src 'none'; base-uri 'none'")
        response.headers["Cache-Control"] = "no-store"
        return response

    return application
