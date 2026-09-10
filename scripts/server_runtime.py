"""One-command controller for the local public-test stack."""
import argparse
from argparse import Namespace
import json
import os
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.parse import urlsplit

from dotenv import dotenv_values
import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.local_runtime import (  # noqa: E402
    Runtime,
    free_port,
    matches,
    model_command,
    ready,
    wait_ready,
)
from scripts.remote_preflight import inspect  # noqa: E402

PUBLIC_STATE = ROOT / ".runtime" / "public-test.json"


def load_config(path):
    source = Path(path).resolve()
    if not source.is_file():
        raise RuntimeError("Public test config is missing: .runtime/public-test.env")
    values = dict(dotenv_values(source, interpolate=False))
    required = ("NPC_MODEL", "NPC_API_KEY", "LLAMA_MODEL_PATH", "LLAMA_SERVER_PATH",
                "NPC_DATABASE_PATH", "NPC_GUEST_SECRET")
    if any(not values.get(key) for key in required):
        raise RuntimeError("Public test config is incomplete; restore .runtime/public-test.env")
    return source, values


def tunnel_origin(text):
    found = re.findall(r"https://[a-z0-9-]+\.trycloudflare\.com", text)
    return found[-1] if found else None


def http_ok(url, *, headers=None, timeout=2):
    try:
        with httpx.Client(timeout=timeout, trust_env=False, follow_redirects=True) as client:
            return client.get(url, headers=headers).status_code == 200
    except httpx.HTTPError:
        return False


def wait_http(record, url, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not matches(record):
            raise RuntimeError("Owned process exited before readiness.")
        if http_ok(url):
            return
        time.sleep(0.25)
    raise RuntimeError("Readiness timed out; check .runtime logs.")


def write_config(path, values):
    text = "\n".join(key + "=" + json.dumps(value) for key, value in values.items() if value is not None)
    Path(path).write_text(text + "\n", encoding="utf-8")


def current_origin(values):
    if PUBLIC_STATE.is_file():
        try:
            return json.loads(PUBLIC_STATE.read_text(encoding="utf-8")).get("origin")
        except (ValueError, TypeError, AttributeError):
            pass
    return values.get("NPC_PUBLIC_ORIGIN")


def model_args(values):
    return Namespace(
        action="start-llm",
        executable=values["LLAMA_SERVER_PATH"],
        model=values["LLAMA_MODEL_PATH"],
        alias=values["NPC_MODEL"],
        min_free_mib=2048,
        context=int(values.get("LLAMA_CONTEXT", "4096")),
        gpu_layers=values.get("LLAMA_GPU_LAYERS", "auto"),
        timeout=180,
        max_tokens=int(values.get("NPC_MAX_TOKENS", "256")),
        reuse_llm=False,
    )


def start_stack(env_file):
    source, values = load_config(env_file)
    runtime = Runtime()
    spawned = []
    with runtime.locked():
        llm = runtime.state.get("llm")
        if matches(llm):
            if not ready("http://127.0.0.1:8001/v1/models", values["NPC_MODEL"], values["NPC_API_KEY"]):
                raise RuntimeError("Owned model is running but its alias or readiness does not match.")
        else:
            runtime.stop("llm")
            free_port(8001)
            args = model_args(values)
            environment = dict(os.environ, **{key: value for key, value in values.items() if value is not None})
            llm = runtime.launch("llm", model_command(args), environment)
            spawned.append("llm")
            wait_ready(llm, "http://127.0.0.1:8001/v1/models", args.timeout,
                       values["NPC_MODEL"], values["NPC_API_KEY"])

        origin = current_origin(values)
        complete = all(matches(runtime.state.get(name)) for name in ("web", "admin", "tunnel"))
        if (complete and http_ok("http://127.0.0.1:8000/api/live")
                and http_ok("http://127.0.0.1:8002/api/ready") and origin and http_ok(origin, timeout=5)):
            print("Already running")
            print("Chat:", origin)
            print("Inspector: http://127.0.0.1:8002/inspector")
            return

        for name in ("admin", "web", "tunnel"):
            runtime.stop(name)
        try:
            for port in (8000, 8002):
                free_port(port)
            cloudflared = shutil.which("cloudflared")
            if not cloudflared:
                raise RuntimeError("cloudflared is missing from PATH.")
            tunnel = runtime.launch("tunnel", [cloudflared, "tunnel", "--url",
                "http://127.0.0.1:8000", "--no-autoupdate"], dict(os.environ))
            spawned.append("tunnel")
            deadline = time.monotonic() + 60
            origin = None
            while time.monotonic() < deadline:
                origin = tunnel_origin((runtime.directory / "tunnel.log").read_text(errors="replace"))
                if origin:
                    break
                if not matches(tunnel):
                    raise RuntimeError("Quick Tunnel exited before issuing a URL.")
                time.sleep(0.5)
            if not origin:
                raise RuntimeError("Quick Tunnel did not issue a URL.")

            values["NPC_PUBLIC_ORIGIN"] = origin
            checked = inspect(values)
            if not checked["configuration_ready"]:
                raise RuntimeError("Public test config failed preflight: " + "; ".join(checked["errors"]))
            write_config(source, values)
            environment = dict(os.environ)
            web = runtime.launch("web", [sys.executable, "scripts/serve_remote.py",
                                         "--env-file", str(source)], environment)
            spawned.append("web")
            wait_http(web, "http://127.0.0.1:8000/api/live", 30)
            host = urlsplit(origin).netloc
            if not http_ok("http://127.0.0.1:8000/", headers={"Host": host}):
                raise RuntimeError("Guest web did not accept the tunnel host.")

            admin = runtime.launch("admin", [sys.executable, "scripts/serve_admin.py",
                                              "--env-file", str(source)], environment)
            spawned.append("admin")
            wait_ready(admin, "http://127.0.0.1:8002/api/ready", 60)
            PUBLIC_STATE.write_text(json.dumps({"origin": origin,
                "database": values["NPC_DATABASE_PATH"]}, indent=2), encoding="utf-8")
            print("Started")
            print("Chat:", origin)
            print("Inspector: http://127.0.0.1:8002/inspector")
        except BaseException:
            for name in reversed(spawned):
                runtime.stop(name)
            raise


def stop_stack():
    runtime = Runtime()
    with runtime.locked():
        for name in ("admin", "tunnel", "web", "llm"):
            runtime.stop(name)
    print("Stopped")


def status_stack(env_file):
    _, values = load_config(env_file)
    runtime = Runtime()
    with runtime.locked():
        states = {name: matches(runtime.state.get(name)) for name in ("llm", "web", "admin", "tunnel")}
    print("Model:", "running" if states["llm"] and ready(
        "http://127.0.0.1:8001/v1/models", values["NPC_MODEL"], values["NPC_API_KEY"]) else "stopped")
    print("Web:", "running" if states["web"] and http_ok("http://127.0.0.1:8000/api/live") else "stopped")
    print("Inspector:", "running" if states["admin"] and http_ok(
        "http://127.0.0.1:8002/api/ready") else "stopped")
    origin = current_origin(values)
    public = bool(states["tunnel"] and origin and http_ok(origin, timeout=5))
    print("Public:", origin if public else "stopped")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop", "restart", "status"))
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    try:
        if args.action in {"stop", "restart"}:
            stop_stack()
        if args.action in {"start", "restart"}:
            start_stack(args.env_file)
            return 0
        if args.action == "status":
            return status_stack(args.env_file)
        return 0
    except (RuntimeError, OSError, ValueError) as exc:
        print("ERROR:", str(exc) if type(exc) is RuntimeError else type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
