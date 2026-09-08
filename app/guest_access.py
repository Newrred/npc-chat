"""Automatic browser identity and durable limits for a public link deployment."""
from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib
import hmac
from http.cookies import SimpleCookie, CookieError
from pathlib import Path
import secrets
import sqlite3
import time

from app.errors import ChatError


COOKIE = "__Host-npc_guest"
LIFETIME = 30 * 86400


class GuestIdentity:
    def __init__(self, secret):
        self.secret = secret.encode()

    def identify(self, raw, now=None):
        now = int(time.time() if now is None else now)
        cookies = SimpleCookie()
        try:
            cookies.load(raw)
            token = cookies[COOKIE].value if COOKIE in cookies else ""
            identity, expiry, signature = token.split(".")
            payload = identity + "." + expiry
            expected = hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()
            if (len(identity) == 64 and all(c in "0123456789abcdef" for c in identity)
                    and now < int(expiry) <= now + LIFETIME
                    and hmac.compare_digest(expected, signature)):
                return "guest:" + identity, None
        except (ValueError, CookieError):
            pass
        # Missing, expired or tampered tokens never inherit the previous browser's profile.
        identity = secrets.token_hex(32)
        payload = identity + "." + str(now + LIFETIME)
        signature = hmac.new(self.secret, payload.encode(), hashlib.sha256).hexdigest()
        cookie = f"{COOKIE}={payload}.{signature}; Path=/; Secure; HttpOnly; SameSite=Lax; Max-Age={LIFETIME}"
        return "guest:" + identity, cookie


class GuestLimits:
    """Companion SQLite file: quotas survive app restart and cookie resets cannot bypass the total cap."""
    def __init__(self, path, config):
        self.path, self.config = Path(path), config

    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute("CREATE TABLE IF NOT EXISTS visits (owner TEXT PRIMARY KEY, seen REAL NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS usage (day TEXT NOT NULL, owner TEXT NOT NULL, count INTEGER NOT NULL, PRIMARY KEY(day, owner))")
        return db

    def admit(self, owner, *, charge=False, now=None):
        now = time.time() if now is None else now
        day = datetime.fromtimestamp(now, timezone(timedelta(hours=9))).date().isoformat()
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                db.execute("DELETE FROM visits WHERE seen <= ?", (now - self.config.visitor_ttl,))
                present = db.execute("SELECT 1 FROM visits WHERE owner=?", (owner,)).fetchone()
                if not present and db.execute("SELECT COUNT(*) FROM visits").fetchone()[0] >= self.config.active_visitors:
                    raise ChatError("VISITOR_CAPACITY", "현재 이용자가 많습니다. 잠시 후 다시 이용해 주세요.", 429, True)
                if charge:
                    total = db.execute("SELECT COALESCE(SUM(count),0) FROM usage WHERE day=?", (day,)).fetchone()[0]
                    used = db.execute("SELECT count FROM usage WHERE day=? AND owner=?", (day, owner)).fetchone()
                    if total >= self.config.daily_total:
                        raise ChatError("DAILY_TOTAL_LIMIT", "오늘의 전체 이용 한도에 도달했습니다. 내일 다시 이용해 주세요.", 429, False)
                    if used and used[0] >= self.config.daily_visitor:
                        raise ChatError("DAILY_VISITOR_LIMIT", "오늘 이 브라우저의 이용 한도에 도달했습니다. 내일 다시 이용해 주세요.", 429, False)
                    db.execute("INSERT INTO usage VALUES(?,?,1) ON CONFLICT(day,owner) DO UPDATE SET count=count+1", (day, owner))
                    # Only quota counters are pruned, never conversation data.
                    db.execute("DELETE FROM usage WHERE day < ?", (day,))
                db.execute("INSERT INTO visits VALUES(?,?) ON CONFLICT(owner) DO UPDATE SET seen=excluded.seen", (owner, now))
                db.execute("COMMIT")
            except BaseException:
                db.execute("ROLLBACK")
                raise
