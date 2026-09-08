"""Run the administrator viewer on this computer only."""
import argparse
from pathlib import Path
import sys

from dotenv import dotenv_values
import uvicorn


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", required=True)
    args = parser.parse_args()
    values = dotenv_values(args.env_file)
    database = values.get("NPC_DATABASE_PATH")
    if not database or not Path(database).is_file():
        parser.error("The selected environment must contain an existing NPC_DATABASE_PATH")
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app.admin import create_admin
    uvicorn.run(create_admin(database), host="127.0.0.1", port=8002, access_log=False)


if __name__ == "__main__":
    main()
