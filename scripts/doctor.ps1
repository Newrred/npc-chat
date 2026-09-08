[CmdletBinding()]
param([string]$Python = "")

$ErrorActionPreference = "Stop"
$repositoryRoot = Split-Path -Parent $PSScriptRoot
if (-not $Python) {
    $projectPython = Join-Path $repositoryRoot "venv/Scripts/python.exe"
    $alternatePython = Join-Path $repositoryRoot ".venv/Scripts/python.exe"
    if (Test-Path -LiteralPath $projectPython) { $Python = $projectPython }
    elseif (Test-Path -LiteralPath $alternatePython) { $Python = $alternatePython }
    else { $Python = "python" }
}

# Read-only: no install, service startup, state writes, model load, or generation.
$probe = @'
import asyncio
import importlib.metadata
import socket
import subprocess
import sys
from urllib.parse import urlparse

print("Python:", sys.version.split()[0])
missing = []
for name in ("fastapi", "uvicorn", "openai", "httpx", "python-dotenv", "SQLAlchemy", "alembic", "psutil", "pytest", "ruff"):
    try:
        print(name + ":", importlib.metadata.version(name))
    except importlib.metadata.PackageNotFoundError:
        missing.append(name)
        print(name + ": MISSING")

try:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,driver_version", "--format=csv,noheader"],
        capture_output=True, text=True, timeout=5,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    print("GPU:", result.stdout.strip() if result.returncode == 0 else "query unavailable")
except (OSError, subprocess.TimeoutExpired):
    print("GPU: nvidia-smi unavailable (offline tests do not require a GPU)")

for port in (8000, 8001):
    with socket.socket() as probe:
        probe.settimeout(1)
        listening = probe.connect_ex(("127.0.0.1", port)) == 0
    print("Reference port", port, "LISTENING" if listening else "CLOSED")

if missing:
    print("Install the documented development requirements before running checks.")
    raise SystemExit(1)

try:
    from app.config import settings
    from app.services.health_service import check_dependencies, check_llm
    from app.repository import SQLiteRepository
    from pathlib import Path
    import os
    import shutil
    from scripts.local_runtime import Runtime, matches
    print("Model file:", "FOUND" if Path(os.getenv("LLAMA_MODEL_PATH", "")).is_file() else "MISSING")
    print("llama-server:", "FOUND" if shutil.which(os.getenv("LLAMA_SERVER_PATH", "llama-server.exe")) else "MISSING")
    print("Configured context:", os.getenv("LLAMA_CONTEXT", "2048"), "completion cap:", settings.llm_max_tokens)
    print("Contract:", settings.llm_output_contract, "JSON mode:", settings.llm_json_mode)
    print("Token count mode:", settings.token_count_mode)
    import json
    registry = Runtime().path
    if registry.exists():
        for name, record in json.loads(registry.read_text()).items():
            print("Owned", name, "RUNNING" if matches(record) else "STALE")
except Exception as exc:
    print("Configuration load failed:", type(exc).__name__)
    raise SystemExit(1)

# Never print configured URLs or credentials. Honor the backend's .env/settings.
port_conflict = urlparse(settings.llm_base_url).port == 8000
if port_conflict:
    print("LLM config: port 8000 conflicts with the reference backend port; use 8001.")

async def inspect():
    store = SQLiteRepository(settings.database_path)
    try:
        return await check_dependencies(
            {"database": store.ping, "llm": check_llm}, timeout_sec=settings.health_timeout_sec
        )
    finally:
        await store.close()

results = asyncio.run(inspect())
for name, status in results.items():
    print("Configured " + name + ":", status)
print("Readiness probes do not validate generation quality, model ID, or VRAM fit.")
raise SystemExit(0 if not port_conflict and all(value == "ok" for value in results.values()) else 1)
'@

Push-Location -LiteralPath $repositoryRoot
try {
    & $Python -c $probe
    $doctorExitCode = $LASTEXITCODE
}
finally { Pop-Location }
exit $doctorExitCode
