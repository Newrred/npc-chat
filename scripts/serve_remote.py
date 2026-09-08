"""Start only the authenticated web app from an explicit private deployment configuration."""
import argparse
import logging
import os
from pathlib import Path
import sys

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.remote_preflight import inspect  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    path = Path(args.env_file).resolve()
    if not path.is_file():
        parser.error("Private deployment configuration is missing")
    values = dotenv_values(path, interpolate=False)
    result = inspect(values)
    if not result["configuration_ready"]:
        parser.error("Deployment configuration is incomplete; run remote_preflight.py")
    # Never inherit development .env values or serve an accidentally unauthenticated app.
    for key in list(os.environ):
        if key.startswith(("NPC_", "COMFY_", "LLAMA_")) or key == "CORS_ORIGINS":
            del os.environ[key]
    os.environ["PYTHON_DOTENV_DISABLED"] = "1"
    os.environ.update({key: value for key, value in values.items() if value is not None})
    os.environ["NPC_ACCESS_MODE"] = values["NPC_ACCESS_MODE"]
    logger = logging.getLogger("app.remote_access")
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    logger.propagate = False
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, workers=1,
                access_log=False, proxy_headers=False)


if __name__ == "__main__":
    main()
