"""Opt-in loopback HTTP smoke: python -m tests.smoke_local (no model/Redis needed)."""

import argparse
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
import socket
import threading
import time

import httpx
import uvicorn


class ModelStub(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass

    def respond(self, status, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/v1/models":
            self.respond(200, {"object": "list", "data": [{"id": "smoke-model", "object": "model"}]})
        else:
            self.respond(404, {})

    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.respond(404, {})
            return
        request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        assert request["model"] == "smoke-model"
        assert request["max_tokens"] == 256
        self.respond(200, {
            "id": "smoke-completion", "object": "chat.completion", "created": 0, "model": "smoke-model",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {
                "role": "assistant", "content": json.dumps({
                    "reply": "오늘도 와 줬네. 반가워.", "face": "shy smile", "internal_emotion": "happy",
                    "schema_version": 1, "emotion_tags": ["기쁨"], "flags_set": [],
                    "interaction": {"type": "neutral", "intensity": 0}, "memory_candidates": [],
                }, ensure_ascii=False),
            }}],
        })


def serve_http(stack, handler, port):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    def stop():
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    stack.callback(stop)
    return server.server_address[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-port", type=int, default=0)
    parser.add_argument("--llm-port", type=int, default=0)
    parser.add_argument("--serve-seconds", type=int, default=0, help="Keep synthetic services open for browser QA")
    args = parser.parse_args()
    with ExitStack() as stack:
        llm_port = serve_http(stack, ModelStub, args.llm_port)
        # Override only this process, before importing any application settings.
        for name in list(os.environ):
            if name.startswith(("NPC_", "COMFY_", "REDIS_", "SESSION_", "HEALTH_")) or name == "CORS_ORIGINS":
                os.environ.pop(name)
        os.environ.update(
            PYTHON_DOTENV_DISABLED="1", NPC_LLM_BACKEND="llama_cpp",
            NPC_BASE_URL=f"http://127.0.0.1:{llm_port}/v1", NPC_MODEL="smoke-model",
            NPC_API_KEY="local-smoke-only", COMFY_ENABLED="false", COMFY_CONNECT="false",
        )
        # Also protect environments with older python-dotenv versions.
        from unittest.mock import patch
        with patch("dotenv.load_dotenv", return_value=False):
            from app.main import create_app
            from tests.fakes import FakeStore

        store = FakeStore()
        application = create_app(session_store=store)
        listener = socket.socket()
        listener.bind(("127.0.0.1", args.backend_port))
        backend_port = listener.getsockname()[1]
        stack.callback(listener.close)
        server = uvicorn.Server(uvicorn.Config(application, log_level="error", access_log=False))
        worker = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
        worker.start()

        def stop_backend():
            server.should_exit = True
            worker.join(timeout=5)

        stack.callback(stop_backend)
        deadline = time.monotonic() + 10
        while not server.started:
            if not worker.is_alive() or time.monotonic() >= deadline:
                raise RuntimeError("Smoke backend failed to start")
            time.sleep(0.05)

        with httpx.Client(base_url=f"http://127.0.0.1:{backend_port}", timeout=5, trust_env=False) as client:
            assert client.get("/api/unknown").status_code == 404
            assert client.get("/api/chat").status_code == 405
            assert client.get("/.env").status_code == 404
            assert client.get("/").status_code == 200
            assert client.get("/api/live").status_code == 200
            assert client.get("/api/health").json() == {"status": "ok"}
            assert client.get("/api/ready").status_code == 200
            assert client.post("/api/chat", json={"message": ""}).status_code == 422
            response = client.post("/api/chat", json={"message": "테스트 인사", "comfy_on": False})
            assert response.status_code == 200, response.text
            assert response.json()["reply"] == "오늘도 와 줬네. 반가워."
            assert response.json()["affection_total"] == 0
            assert response.json()["comfy_status"] == "disabled"
            store.ping_error = ConnectionError("injected failure")
            assert client.get("/api/ready").status_code == 503
            assert client.get("/api/live").status_code == 200
            store.ping_error = None
            assert client.get("/api/ready").status_code == 200

        with httpx.Client(timeout=5, trust_env=False) as client:
            for asset in ("index.html", "config.js", "app.js", "faces/neutral.png", "faces/shy_smile.png"):
                assert client.get(f"http://127.0.0.1:{backend_port}/{asset}").status_code == 200
        print("PASS: HTTP liveness, readiness, outage/recovery, invalid request, real adapter + stub chat, assets")
        if args.serve_seconds:
            print(f"Synthetic browser QA: http://127.0.0.1:{backend_port}", flush=True)
            time.sleep(max(0, min(args.serve_seconds, 600)))
    assert store.closed
    print("PASS: smoke services stopped; no persistent conversation state written")


if __name__ == "__main__":
    main()
