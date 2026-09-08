"""Offline SQLite maintenance; Redis is imported only for explicit legacy export."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import settings  # noqa: E402
from app.character_config import load_character_config  # noqa: E402
from app.repository import SQLiteRepository  # noqa: E402


def export_redis(destination):
    import redis
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Export destination must be new")
    prefix = (settings.redis_key_prefix or "npc").strip() or "npc"
    entries = []
    source = hashlib.sha256(settings.redis_url.encode()).hexdigest()
    with redis.Redis.from_url(settings.redis_url, decode_responses=True,
                              socket_connect_timeout=3, socket_timeout=3) as client:
        for key in sorted(client.scan_iter(match=prefix + ":session:*")):
            raw = client.get(key)
            if raw:
                entries.append({"source_id": hashlib.sha256((source + key).encode()).hexdigest(),
                                "session_id": key[len(prefix + ":session:"):], "raw": json.loads(raw)})
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8") as output:
        json.dump({"format": 1, "entries": entries}, output, ensure_ascii=False)
    return len(entries)


def restore(repo, source):
    source = Path(source).resolve()
    if source == repo.path or not source.is_file():
        raise ValueError("Restore source must be a separate existing backup")
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as incoming:
        if incoming.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("Invalid backup")
        if incoming.execute("SELECT version_num FROM alembic_version").fetchone() != ("0001",):
            raise ValueError("Unsupported backup schema")
        if repo.path.exists():
            repo.backup(repo.path.with_name(f"before-restore-{time.time_ns()}.sqlite3"))
        repo.engine.dispose()
        repo.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(repo.path)) as target:
            incoming.backup(target)
    repo.check()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["upgrade", "status", "backup", "restore", "export-redis", "import-legacy"])
    parser.add_argument("--database", default=settings.database_path)
    parser.add_argument("--file")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.action in ("backup", "restore", "export-redis", "import-legacy") and not args.file:
        parser.error("--file is required")
    repo = SQLiteRepository(args.database)
    try:
        if args.action == "status":
            repo.check()
            print("Database ready: schema 0001")
        elif args.action == "backup":
            repo.backup(args.file)
            print("Verified SQLite backup created")
        else:
            with repo.lease:
                if args.action == "export-redis":
                    print("Legacy records exported:", export_redis(args.file))
                elif args.action == "restore":
                    if not args.apply:
                        print("Dry run: restore requires --apply; stop web first")
                    else:
                        restore(repo, args.file)
                        print("Restore verified; prior database preserved")
                elif args.action == "upgrade":
                    repo.upgrade()
                    repo.check()
                    print("Schema ready")
                else:
                    archive = json.loads(Path(args.file).read_text(encoding="utf-8"))
                    if archive.get("format") != 1:
                        raise ValueError("Unsupported archive")
                    entries = archive["entries"]
                    if not args.apply:
                        # Full validation/migration rehearsal against an isolated temporary DB.
                        import tempfile
                        with tempfile.TemporaryDirectory() as temporary:
                            rehearsal = SQLiteRepository(Path(temporary) / "rehearsal.sqlite3")
                            try:
                                rehearsal.upgrade()
                                import_entries(rehearsal, entries)
                            finally:
                                rehearsal.engine.dispose()
                        print("Dry run validated records:", len(entries))
                    else:
                        if repo.path.exists():
                            repo.backup(repo.path.with_name(f"before-import-{time.time_ns()}.sqlite3"))
                        repo.upgrade()
                        count = import_entries(repo, entries)
                        print("Imported:", count, "already processed:", len(entries) - count)
    except Exception as exc:
        print("Maintenance failed:", type(exc).__name__, file=sys.stderr)
        return 1
    finally:
        repo.engine.dispose()
    return 0


def import_entries(repo, entries):
    character = load_character_config()
    count = 0
    for entry in entries:
        _, created = repo.import_legacy(entry["source_id"], entry["session_id"], entry["raw"],
                                        settings.character_id, character.initial_relationship)
        count += created
    return count


if __name__ == "__main__":
    raise SystemExit(main())
