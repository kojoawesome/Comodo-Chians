import sqlite3
import time
from datetime import datetime, timezone, timedelta
from config import DB_PATH


def _conn():
    return sqlite3.connect(DB_PATH)


def _next_midnight_utc() -> float:
    """Unix timestamp of the next UTC midnight."""
    now = datetime.now(timezone.utc)
    tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    return tomorrow.timestamp()


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS addresses (
                address      TEXT PRIMARY KEY,
                seed_phrase  TEXT NOT NULL,
                checked      INTEGER DEFAULT 0,
                has_balance  INTEGER DEFAULT 0,
                has_tx       INTEGER DEFAULT 0,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS progress (
                id               INTEGER PRIMARY KEY DEFAULT 1,
                total_generated  INTEGER DEFAULT 0,
                total_checked    INTEGER DEFAULT 0
            );
        """)
        # Migrate: add new columns if they don't exist yet
        for col, definition in [
            ("batch_number",    "INTEGER DEFAULT 1"),
            ("api_calls_today", "INTEGER DEFAULT 0"),
            ("daily_reset_at",  "REAL    DEFAULT 0"),
        ]:
            try:
                con.execute(f"ALTER TABLE progress ADD COLUMN {col} {definition}")
            except Exception:
                pass  # column already exists
        con.execute(
            "INSERT OR IGNORE INTO progress "
            "(id, batch_number, total_generated, total_checked, api_calls_today, daily_reset_at) "
            "VALUES (1, 1, 0, 0, 0, ?)",
            (_next_midnight_utc(),),
        )


def save_address(address: str, seed_phrase: str) -> bool:
    """Insert address. Returns True if new, False if duplicate."""
    with _conn() as con:
        cur = con.execute(
            "INSERT OR IGNORE INTO addresses (address, seed_phrase) VALUES (?, ?)",
            (address, seed_phrase),
        )
        return cur.rowcount == 1


def increment_generated() -> None:
    with _conn() as con:
        con.execute("UPDATE progress SET total_generated = total_generated + 1 WHERE id = 1")


def get_pending_batch(n: int) -> list[dict]:
    with _conn() as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT address, seed_phrase FROM addresses WHERE checked = 0 LIMIT ?", (n,)
        ).fetchall()
    return [dict(r) for r in rows]


def mark_checked(address: str, has_balance: bool, has_tx: bool) -> None:
    with _conn() as con:
        con.execute(
            "UPDATE addresses SET checked = 1, has_balance = ?, has_tx = ? WHERE address = ?",
            (int(has_balance), int(has_tx), address),
        )
        con.execute("UPDATE progress SET total_checked = total_checked + 1 WHERE id = 1")


def get_progress() -> dict:
    with _conn() as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT batch_number, total_generated, total_checked, "
            "api_calls_today, daily_reset_at FROM progress WHERE id = 1"
        ).fetchone()
    return dict(row) if row else {}


def add_api_calls(n: int) -> None:
    """Increment today's API call counter."""
    with _conn() as con:
        con.execute("UPDATE progress SET api_calls_today = api_calls_today + ? WHERE id = 1", (n,))


def maybe_reset_daily_calls() -> bool:
    """
    If the daily reset timestamp has passed, zero out api_calls_today and
    set a new reset timestamp. Returns True if a reset happened.
    """
    p = get_progress()
    if time.time() >= p["daily_reset_at"]:
        with _conn() as con:
            con.execute(
                "UPDATE progress SET api_calls_today = 0, daily_reset_at = ? WHERE id = 1",
                (_next_midnight_utc(),),
            )
        return True
    return False


def start_new_batch() -> int:
    """Clear addresses, reset counters, increment batch number. Returns new batch number."""
    with _conn() as con:
        con.execute("DELETE FROM addresses")
        con.execute(
            "UPDATE progress SET "
            "batch_number = batch_number + 1, "
            "total_generated = 0, "
            "total_checked = 0 "
            "WHERE id = 1"
        )
        row = con.execute("SELECT batch_number FROM progress WHERE id = 1").fetchone()
    return row[0]
