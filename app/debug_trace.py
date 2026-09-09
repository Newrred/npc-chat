"""Explicit opt-in, bounded private diagnostics. Never use application content logs."""
from contextlib import contextmanager, closing
from contextvars import ContextVar
import json
import logging
from pathlib import Path
import sqlite3
import time
import uuid

current = ContextVar("npc_debug_trace", default=None)


def trace_path(database):
    return Path(str(database) + ".debug.sqlite3")


def connection(database):
    db = sqlite3.connect(trace_path(database), timeout=1)
    db.execute("CREATE TABLE IF NOT EXISTS traces (id TEXT PRIMARY KEY, updated REAL, payload TEXT)")
    return db


def prune(db):
    db.execute("DELETE FROM traces WHERE updated < ?", (time.time() - 3600,))
    db.execute("DELETE FROM traces WHERE id NOT IN (SELECT id FROM traces ORDER BY updated DESC LIMIT 100)")


def emit(event, **data):
    state = current.get()
    if state is None:
        return
    database, record = state
    record["events"].append({"event": event, "at": time.time(), **data})
    record["updated"] = time.time()
    try:
        with closing(connection(database)) as db, db:
            db.execute("INSERT OR REPLACE INTO traces VALUES (?,?,?)",
                       (record["id"], record["updated"], json.dumps(record, ensure_ascii=False)))
            prune(db)
    except (OSError, sqlite3.Error, TypeError, ValueError):
        logging.getLogger(__name__).warning("debug_trace_write_failed")


@contextmanager
def capture(database, enabled, profile_id, character_id, turn_id):
    record = dict(id=uuid.uuid4().hex, profile_id=profile_id, character_id=character_id,
                  turn_id=turn_id, events=[], updated=time.time())
    token = current.set((database, record) if enabled else None)
    try:
        yield
    except BaseException as exc:
        emit("failed", error_type=type(exc).__name__)
        raise
    finally:
        current.reset(token)


def read(database):
    if not trace_path(database).is_file():
        return []
    with closing(connection(database)) as db, db:
        prune(db)
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM traces ORDER BY updated DESC")]


def forget(database, profile_id, character_id=None):
    if not trace_path(database).is_file():
        return
    try:
        with closing(connection(database)) as db, db:
            for key, raw in db.execute("SELECT id,payload FROM traces").fetchall():
                row = json.loads(raw)
                if row["profile_id"] == profile_id and (character_id is None or row["character_id"] == character_id):
                    db.execute("DELETE FROM traces WHERE id=?", (key,))
    except (OSError, sqlite3.Error):
        logging.getLogger(__name__).warning("debug_trace_cleanup_failed")
