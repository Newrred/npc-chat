"""Loopback-only development launcher. Never adopts or kills a process by port/name."""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

import httpx
import psutil
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
HIDDEN = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def prepare_database():
    sys.path.insert(0, str(ROOT))
    from app.config import settings
    from app.repository import SQLiteRepository
    repo = SQLiteRepository(settings.database_path)
    try:
        with repo.lease:
            repo.upgrade()
            repo.check()
    except Exception:
        raise RuntimeError("SQLite is unavailable or already owned by another app.") from None
    finally:
        repo.engine.dispose()


def identity(pid):
    try:
        process = psutil.Process(pid)
        return {"pid": pid, "created": process.create_time(), "exe": process.exe(), "argv": process.cmdline()}
    except psutil.NoSuchProcess:
        return None


def matches(record):
    return bool(record and identity(record["pid"]) == record)


def stop_owned(record):
    if not matches(record):
        return
    process = psutil.Process(record["pid"])
    process.terminate()
    try:
        process.wait(timeout=10)
    except psutil.TimeoutExpired:
        if matches(record):
            process.kill()
            process.wait(timeout=5)


def free_port(port):
    with socket.socket() as sock:
        try:
            sock.bind(("127.0.0.1", port))
        except OSError:
            raise RuntimeError(f"Port {port} is occupied; its process will not be stopped.") from None


def gpu_info():
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
        capture_output=True, text=True, timeout=10, creationflags=HIDDEN, check=True,
    )
    name, total, free = result.stdout.strip().splitlines()[0].split(",")
    return {"name": name.strip(), "total_mib": int(total), "free_mib": int(free)}


def model_command(args):
    executable = shutil.which(args.executable) if args.executable else None
    if not executable:
        raise RuntimeError("llama-server executable missing; set LLAMA_SERVER_PATH or --executable.")
    model = Path(args.model).expanduser() if args.model else None
    if model is None or not model.is_file() or model.suffix.lower() != ".gguf":
        raise RuntimeError("GGUF missing; set LLAMA_MODEL_PATH or --model. No model is downloaded.")
    gpu = gpu_info()
    print("GPU:", json.dumps(gpu), flush=True)
    if gpu["free_mib"] < args.min_free_mib:
        raise RuntimeError(f"Need at least {args.min_free_mib} MiB free VRAM before loading.")
    help_result = subprocess.run(
        [executable, "--help"], capture_output=True, text=True, errors="replace", timeout=30,
        creationflags=HIDDEN, check=True,
    )
    for flag in ("--fit", "--fit-target", "--reasoning-budget", "--log-disable"):
        if flag not in help_result.stdout:
            raise RuntimeError(f"Installed llama.cpp lacks required {flag}; use a compatible build.")
    return [str(Path(executable).resolve()), "--model", str(model.resolve()), "--alias", args.alias,
            "--host", "127.0.0.1", "--port", "8001", "--ctx-size", str(args.context),
            "--parallel", "1", "--batch-size", "128", "--ubatch-size", "128",
            "--n-gpu-layers", args.gpu_layers,
            "--fit", "on", "--fit-target", "1024", "--reasoning-budget", "0", "--log-disable"]


def ready(url, alias=None, api_key=""):
    try:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        with httpx.Client(timeout=2, trust_env=False) as client:
            response = client.get(url, headers=headers)
            if response.status_code != 200:
                return False
            data = response.json()
            if alias:
                return any(item.get("id") == alias for item in data.get("data", []))
            return data.get("status") == "ready"
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        return False


def wait_ready(record, url, timeout, alias=None, api_key=""):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not matches(record):
            raise RuntimeError("Owned process exited before readiness.")
        if ready(url, alias, api_key):
            return
        time.sleep(0.25)
    raise RuntimeError("Readiness timed out; check the local startup log and available memory.")


class Runtime:
    def __init__(self, directory=ROOT / ".runtime"):
        self.directory = directory
        self.path = directory / "processes.json"
        self.state = {}

    def save(self):
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        temporary.replace(self.path)

    @contextmanager
    def locked(self):
        self.directory.mkdir(parents=True, exist_ok=True)
        # OS advisory byte lock is released even when a launcher crashes.
        with (self.directory / "launcher.lock").open("a+b") as handle:
            handle.seek(0)
            if os.name == "nt":
                import msvcrt
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError:
                    raise RuntimeError("Another launcher is running.") from None
            else:
                import fcntl
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            try:
                self.state = json.loads(self.path.read_text()) if self.path.exists() else {}
                yield
            finally:
                handle.seek(0)
                if os.name == "nt":
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(handle, fcntl.LOCK_UN)

    def launch(self, name, command, env):
        # Only generated commands with no credential arguments are accepted here.
        print("Command:", subprocess.list2cmdline(command), flush=True)
        with (self.directory / f"{name}.log").open("wb") as output:
            process = subprocess.Popen(command, cwd=ROOT, env=env, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=output, creationflags=HIDDEN)
        try:
            record = identity(process.pid)
            if not record:
                raise RuntimeError(f"{name} exited at startup.")
            self.state[name] = record
            self.save()
        except BaseException:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)
            raise
        return record

    def stop(self, name):
        record = self.state.get(name)
        if record:
            stop_owned(record)
            self.state.pop(name)
            self.save()
        print(name + ": stopped or already absent", flush=True)

    def start(self, args):
        local = args.action == "start-local"
        llm_record = self.state.get("llm")
        web_record = self.state.get("web")
        llm_alive, web_alive = matches(llm_record), matches(web_record)
        if local and web_alive:
            if ready("http://127.0.0.1:8000/api/ready"):
                print("Already running: http://127.0.0.1:8000")
                return
            raise RuntimeError("Owned web app is not ready; inspect doctor before stop/restart.")
        if local:
            free_port(8000)
            prepare_database()
        key = os.getenv("NPC_API_KEY", "my-local-key")
        if llm_alive or args.reuse_llm:
            if not ready("http://127.0.0.1:8001/v1/models", args.alias, key):
                raise RuntimeError("Existing model is not ready or alias differs; no process was replaced.")
            command = None
        else:
            free_port(8001)
            command = model_command(args)
        spawned = []
        env = dict(os.environ, NPC_LLM_BACKEND="llama_cpp", NPC_BASE_URL="http://127.0.0.1:8001/v1",
                   NPC_MODEL=args.alias, NPC_MAX_TOKENS=str(args.max_tokens), LLAMA_CONTEXT=str(args.context),
                   NPC_TOKEN_COUNT_MODE=os.getenv("NPC_TOKEN_COUNT_MODE", "llama_cpp"),
                   COMFY_ENABLED="false", COMFY_CONNECT="false")
        try:
            if command:
                record = self.launch("llm", command, env)
                spawned.append("llm")
                wait_ready(record, "http://127.0.0.1:8001/v1/models", args.timeout, args.alias, key)
            if local:
                command = [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
                           "--port", "8000", "--workers", "1", "--no-access-log"]
                record = self.launch("web", command, env)
                spawned.append("web")
                wait_ready(record, "http://127.0.0.1:8000/api/ready", args.timeout)
            print("Ready: " + ("http://127.0.0.1:8000" if local else "http://127.0.0.1:8001/v1"))
        except BaseException:
            for name in reversed(spawned):
                self.stop(name)
            raise


def main():
    load_dotenv(ROOT / ".env")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start-local", "stop-local", "start-llm", "stop-llm", "start-admin", "stop-admin"])
    parser.add_argument("--env-file", help="Selected database environment for start-admin")
    parser.add_argument("--model", default=os.getenv("LLAMA_MODEL_PATH", ""))
    parser.add_argument("--executable", default=os.getenv("LLAMA_SERVER_PATH", "llama-server.exe"))
    parser.add_argument("--alias", default=os.getenv("NPC_MODEL", "local-model"))
    parser.add_argument("--context", type=int, default=int(os.getenv("LLAMA_CONTEXT", "2048")))
    parser.add_argument("--gpu-layers", default=os.getenv("LLAMA_GPU_LAYERS", "12"))
    parser.add_argument("--max-tokens", type=int, default=int(os.getenv("NPC_MAX_TOKENS", "256")))
    parser.add_argument("--min-free-mib", type=int, default=2048)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--reuse-llm", action="store_true")
    args = parser.parse_args()
    if not 512 <= args.context <= 32768 or not 64 <= args.max_tokens <= 2048 or not 1 <= args.timeout <= 600:
        parser.error("context 512..32768, max-tokens 64..2048, timeout 1..600 required")
    try:
        runtime = Runtime()
        with runtime.locked():
            if args.action == "start-admin":
                if not args.env_file or not Path(args.env_file).is_file():
                    raise RuntimeError("start-admin requires an existing --env-file")
                if matches(runtime.state.get("admin")):
                    raise RuntimeError("Admin is already running. Stop it before selecting another database.")
                free_port(8002)
                record = runtime.launch("admin", [sys.executable, "scripts/serve_admin.py", "--env-file",
                                                  str(Path(args.env_file).resolve())], dict(os.environ))
                try:
                    wait_ready(record, "http://127.0.0.1:8002/api/ready", args.timeout)
                except BaseException:
                    runtime.stop("admin")
                    raise
                print("Admin ready: http://127.0.0.1:8002")
            elif args.action == "stop-admin":
                runtime.stop("admin")
            elif args.action.startswith("start"):
                runtime.start(args)
            else:
                if args.action == "stop-local":
                    runtime.stop("admin")
                    runtime.stop("web")
                elif matches(runtime.state.get("web")):
                    raise RuntimeError("Managed web app is running; use stop-local to stop in order.")
                runtime.stop("llm")
    except (RuntimeError, OSError, ValueError, psutil.Error, subprocess.SubprocessError) as exc:
        # Third-party exception strings can contain credentials; only our RuntimeErrors are printed.
        print("ERROR:", str(exc) if type(exc) is RuntimeError else type(exc).__name__, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
