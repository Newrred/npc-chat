"""Loopback-only viewer and scoped test-chat bridge. Never mount on the public app."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse
from app.debug_trace import read as read_traces
from app.conversation_memory import source_views


def create_admin(database, port=8002, *, chat_origin=None, chat_transport=None):
    path = Path(database).resolve()
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    from app.inspector_chat import WRITES, mount_chat
    if chat_origin:
        mount_chat(app, chat_origin, chat_transport, database=path)

    @app.get("/api/prompt-defaults")
    def prompt_defaults():
        from app.character_config import load_character_config
        character = load_character_config()
        identity = character.identity_prompt or ""
        dialogue = character.dialogue_prompt or character.system_prompt
        return {"identity": identity, "dialogue": dialogue.removeprefix(identity).strip()}

    def query(sql, args=()):
        with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as db:
            db.row_factory = sqlite3.Row
            db.execute("PRAGMA query_only=ON")
            return [dict(row) for row in db.execute(sql, args)]

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origins = {f"http://{host}" for host in hosts}
        if (not request.client or request.client.host not in {"127.0.0.1", "::1"}
                or request.headers.get("host") not in hosts
                or request.headers.get("origin", "") not in origins | {""}
                or request.headers.get("sec-fetch-site", "") not in {"", "none", "same-origin"}
                or (request.method not in {"GET", "HEAD"} and not (
                    chat_origin and request.method == "POST" and request.url.path in WRITES
                    and request.headers.get("origin") in origins
                    and request.headers.get("content-type", "").split(";")[0] == "application/json"))):
            return JSONResponse({"error": "Local access only"}, status_code=403)
        response = await call_next(request)
        response.headers.update({"Cache-Control": "no-store", "X-Frame-Options": "DENY",
                                 "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"})
        return response

    @app.exception_handler(sqlite3.Error)
    async def unavailable(_request, _error):
        return JSONResponse({"error": "대화 저장소를 읽을 수 없습니다."}, status_code=503)

    @app.get("/")
    def index():
        return FileResponse(Path(__file__).resolve().parents[1] / "admin" / "index.html")

    @app.get("/api/ready")
    def ready():
        query("SELECT id FROM profiles LIMIT 1")
        return {"status": "ready"}

    @app.get("/inspector")
    def inspector():
        return FileResponse(Path(__file__).resolve().parents[1] / "admin" / "inspector.html")

    @app.get("/inspector.js")
    def inspector_script():
        return FileResponse(Path(__file__).resolve().parents[1] / "admin" / "inspector.js", media_type="text/javascript")

    @app.get("/api/inspector")
    def inspect(profile_id: str = Query(default="", max_length=128),
                character_id: str = Query(default="default", max_length=64),
                trace_id: str = Query(default="", max_length=64)):
        live = {(r["profile_id"], r["character_id"]) for r in query("SELECT profile_id,character_id FROM sessions")}
        traces = [r for r in read_traces(path) if (r["profile_id"], r["character_id"]) in live]
        listing = [{k: r[k] for k in ("id", "profile_id", "character_id", "turn_id", "updated")} |
                   {"status": r["events"][-1]["event"] if r["events"] else "starting"} for r in traces]
        selected = [r for r in traces if r["profile_id"] == profile_id and r["character_id"] == character_id]
        selected = [r for r in selected if r["id"] == trace_id] if trace_id else selected[:1]
        args = (profile_id, character_id)
        stored = query("SELECT kind,content,source_turn,importance FROM memories WHERE profile_id=? AND character_id=?", args)
        raw = query("SELECT client_turn_id,user_message,decision FROM turns WHERE profile_id=? AND character_id=? ORDER BY created,client_turn_id", args)
        for row in raw:
            row["decision"] = json.loads(row["decision"])
        profile = source_views(raw, "")
        from app.conversation_memory import dialogue_events
        episodes = [event for row in raw for event in dialogue_events(row["user_message"], row["decision"]["reply"], row["client_turn_id"])]
        return {"chat_enabled": bool(chat_origin),
            "rooms": [{"profile_id": p, "character_id": c} for p, c in sorted(live)],
            "traces": listing, "detail": selected, "current_memory": {
            "stored_user_memories": stored, "derived_profile": profile, "derived_events_latest_50": episodes[-50:]},
            "retention": "최근 1시간 · 최대 100회 처리. 추적 활성화 이후 요청만 표시합니다."}

    @app.get("/api/rooms")
    def rooms(offset: int = Query(default=0, ge=0)):
        rows = query("SELECT profile_id, character_id, count(*) AS turns, max(created) AS updated "
                     "FROM turns GROUP BY profile_id, character_id "
                     "ORDER BY updated DESC, profile_id, character_id LIMIT 101 OFFSET ?", (offset,))
        return {"items": rows[:100], "next": offset + 100 if len(rows) > 100 else None}

    @app.get("/api/turns")
    def history(profile_id: str = Query(max_length=128), character_id: str = Query(max_length=64),
                before: str | None = Query(default=None, max_length=128)):
        args = [profile_id, character_id]
        where = "profile_id=? AND character_id=?"
        if before:
            cursor = query("SELECT created FROM turns WHERE " + where + " AND client_turn_id=?",
                           (*args, before))
            if not cursor:
                return JSONResponse({"error": "대화가 변경되었습니다. 다시 선택해 주세요."}, status_code=409)
            where += " AND (created < ? OR (created = ? AND client_turn_id < ?))"
            args.extend([cursor[0]["created"], cursor[0]["created"], before])
        rows = query("SELECT client_turn_id, user_message, response, created FROM turns WHERE " + where
                     + " ORDER BY created DESC, client_turn_id DESC LIMIT 51", args)
        return {"items": [{"turn_id": r["client_turn_id"], "user_message": r["user_message"],
                           "reply": json.loads(r["response"])["reply"], "created": r["created"]}
                          for r in reversed(rows[:50])],
                "before": rows[49]["client_turn_id"] if len(rows) > 50 else None}
    return app
