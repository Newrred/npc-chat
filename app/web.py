from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"


def mount_frontend(application: FastAPI) -> None:
    """Expose explicit public files, never the repository or a catch-all SPA route."""
    for url, name in {
        "/": "index.html", "/index.html": "index.html", "/app.js": "app.js",
        "/config.js": "config.js", "/styles.css": "styles.css",
    }.items():
        def handler_factory(filename):
            def serve():
                path = (FRONTEND_DIR / filename).resolve()
                if path.parent != FRONTEND_DIR.resolve() or not path.is_file():
                    raise HTTPException(404)
                return FileResponse(path)
            return serve

        application.add_api_route(url, handler_factory(name), methods=["GET", "HEAD"], include_in_schema=False)

    @application.get("/faces/{filename}", include_in_schema=False)
    def face_file(filename: str):
        directory = (FRONTEND_DIR / "faces").resolve()
        path = (directory / filename).resolve()
        if (directory.parent != FRONTEND_DIR.resolve() or path.parent != directory
                or path.suffix.lower() != ".png" or not path.is_file()):
            raise HTTPException(404)
        return FileResponse(path)

    @application.get("/characters/{character_id}/faces/{filename}", include_in_schema=False)
    def character_face_file(character_id: str, filename: str):
        characters = (FRONTEND_DIR / "characters").resolve()
        directory = (characters / character_id / "faces").resolve()
        path = (directory / filename).resolve()
        if (directory.parent.parent != characters or path.parent != directory
                or path.suffix.lower() != ".png" or not path.is_file()):
            raise HTTPException(404)
        return FileResponse(path)
