"""Desktop-owned model/app supervisor. stdin EOF also requests shutdown."""
import argparse
import json
import os
from pathlib import Path
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv  # noqa: E402
from scripts.local_runtime import Runtime, free_port, matches, model_command, ready  # noqa: E402
from scripts.desktop_config import load_package  # noqa: E402


def wait(record, url, token, stopped, alias=None, timeout=180):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if stopped.is_set():
            raise RuntimeError("START_CANCELLED")
        if not matches(record):
            raise RuntimeError("PROCESS_EXITED")
        if ready(url, alias, token):
            return
        stopped.wait(.25)
    raise RuntimeError("START_TIMEOUT")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--fake", action="store_true")
    args = parser.parse_args()
    token = os.environ.get("NPC_DESKTOP_TOKEN")
    if not token or len(token) < 32:
        raise RuntimeError("MISSING_DESKTOP_TOKEN")
    if (ROOT / "desktop-package.json").is_file():
        os.environ.update(load_package(ROOT))
    else:
        load_dotenv(ROOT / ".env", override=False)
    directory = Path(args.data_dir).resolve()
    stopped = threading.Event()

    def monitor_parent():
        sys.stdin.readline()  # stop command or parent pipe EOF
        stopped.set()

    threading.Thread(target=monitor_parent, daemon=True).start()
    runtime = Runtime(directory / "runtime")
    env = dict(os.environ, NPC_DATABASE_PATH=str(directory / "data/chat.sqlite3"),
               NPC_DEBUG_TRACE="0", NPC_METRICS_ENABLED="0", COMFY_ENABLED="false", COMFY_CONNECT="false",
               NPC_BASE_URL="http://127.0.0.1:8001/v1", NPC_API_KEY=token, LLAMA_API_KEY=token,
               NPC_DESKTOP_TEST="1" if args.fake else "0", CORS_ORIGINS="http://127.0.0.1:8003")
    (directory / "data").mkdir(parents=True, exist_ok=True)
    with runtime.locked():
        # Only our previous registry is eligible for recovery, never another stack.
        runtime.stop("web")
        runtime.stop("llm")
        try:
            free_port(8003)
            if not args.fake:
                free_port(8001)
                model_args = argparse.Namespace(
                    executable=os.getenv("LLAMA_SERVER_PATH", "llama-server"),
                    model=os.getenv("LLAMA_MODEL_PATH", ""), alias=os.getenv("NPC_MODEL", "local-model"),
                    context=int(os.getenv("LLAMA_CONTEXT", "4096")),
                    gpu_layers=os.getenv("LLAMA_GPU_LAYERS", "auto"), min_free_mib=2048)
                record = runtime.launch("llm", model_command(model_args), env)
                wait(record, "http://127.0.0.1:8001/v1/models", token, stopped, model_args.alias)
            if stopped.is_set():
                raise RuntimeError("START_CANCELLED")
            record = runtime.launch("web", [sys.executable, "-m", "uvicorn", "scripts.desktop_server:create_desktop_app",
                                            "--factory", "--host", "127.0.0.1", "--port", "8003",
                                            "--no-access-log"], env)
            wait(record, "http://127.0.0.1:8003/api/ready", token, stopped)
            print(json.dumps({"desktop": "ready"}), flush=True)
            while not stopped.wait(.5):
                if not matches(runtime.state.get("web")) or (not args.fake and not matches(runtime.state.get("llm"))):
                    raise RuntimeError("PROCESS_EXITED")
        finally:
            runtime.stop("web")
            runtime.stop("llm")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"desktop": "error", "type": type(exc).__name__,
                          "message": str(exc) if type(exc) is RuntimeError else "START_FAILED"}), flush=True)
        sys.exit(1)
