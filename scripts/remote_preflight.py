"""Read-only checks for an explicit remote configuration; never publish or print secrets."""
import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.remote_access import RemoteConfig  # noqa: E402


def inspect(values):
    errors = []
    try:
        config = RemoteConfig(mode=values.get("NPC_ACCESS_MODE", ""),
                              origin=values.get("NPC_PUBLIC_ORIGIN", ""),
                              issuer=values.get("NPC_ACCESS_ISSUER", ""),
                              audience=values.get("NPC_ACCESS_AUDIENCE", ""),
                              guest_secret=values.get("NPC_GUEST_SECRET", ""),
                              active_visitors=int(values.get("NPC_ACTIVE_VISITORS", "5")),
                              visitor_ttl=int(values.get("NPC_VISITOR_TTL", "300")),
                              daily_total=int(values.get("NPC_DAILY_TOTAL", "200")),
                              daily_visitor=int(values.get("NPC_DAILY_VISITOR", "30")),
                              requests_per_minute=int(values.get("NPC_REQUESTS_PER_MINUTE", "20")))
        config.validate()
        if config.mode not in {"cloudflare", "guest"}:
            errors.append("Remote deployment requires cloudflare or guest mode")
    except (ValueError, TypeError):
        errors.append("Remote authentication/origin configuration is incomplete or invalid")
    database = Path(values.get("NPC_DATABASE_PATH") or ".")
    if not database.is_absolute() or database.resolve().is_relative_to(ROOT):
        errors.append("Database must use an absolute persistent path outside the application checkout")
    llm = urlsplit(values.get("NPC_BASE_URL") or "")
    if (llm.scheme != "http" or llm.hostname != "127.0.0.1" or llm.port != 8001
            or llm.path != "/v1" or llm.username or llm.password or llm.query or llm.fragment):
        errors.append("Model endpoint must be http://127.0.0.1:8001/v1")
    for key in ("LLAMA_MODEL_PATH", "LLAMA_SERVER_PATH"):
        path = Path(values.get(key) or ".")
        if not path.is_absolute() or not path.is_file():
            errors.append(key + " must identify an existing absolute file")
    if not values.get("NPC_MODEL"):
        errors.append("NPC_MODEL is required")
    if values.get("NPC_TOKEN_COUNT_MODE") != "llama_cpp":
        errors.append("Real tokenizer budgeting is required")
    if any(values.get(key, "").lower() != "false" for key in ("COMFY_ENABLED", "COMFY_CONNECT")):
        errors.append("Optional image generation must remain disabled for this deployment profile")
    return {"configuration_ready": not errors, "errors": errors,
            "release_ready": False,
            "external_gates": ["Selected access mode and HTTPS tunnel verification", "Retention/deletion policy approval",
                               "Backup/restore and restart recovery rehearsal", "Multi-user load and quality review"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    source = Path(args.env_file)
    if not source.is_file():
        parser.error("Configuration file does not exist")
    try:
        result = inspect(dotenv_values(source, interpolate=False))
    except (ValueError, TypeError):
        result = {"configuration_ready": False, "release_ready": False, "errors": ["Invalid configuration"]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["configuration_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
