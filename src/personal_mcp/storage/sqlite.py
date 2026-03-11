from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

_CREATE_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts         TEXT NOT NULL,
    domain     TEXT NOT NULL,
    kind       TEXT,
    dedup_key  TEXT,
    raw        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_domain ON events (domain);
"""

_DEDUP_INDEX_DDL = (
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_events_dedup_key"
    " ON events (dedup_key) WHERE dedup_key IS NOT NULL;"
)


def _github_dedup_key(record: Dict[str, Any]) -> Optional[str]:
    """Return a stable dedup key for GitHub events, or None for other sources.

    The key space is shared across github_sync and github_ingest so that
    events written by either tool are deduplicated against each other.
    """
    if record.get("source") == "github":
        eid = record.get("data", {}).get("github_event_id")
        if eid:
            return f"github:{eid}"
    return None


def _backfill_dedup_keys(conn: sqlite3.Connection) -> None:
    """Populate missing dedup keys for rows created before the #307 schema.

    If older DBs already contain multiple rows for the same GitHub event, only
    the earliest row is backfilled. Later duplicates keep NULL so history is
    preserved while future inserts are still blocked by the keyed row.
    """
    existing_keys = {
        dedup_key
        for (dedup_key,) in conn.execute("SELECT dedup_key FROM events WHERE dedup_key IS NOT NULL")
    }
    updates: list[tuple[str, int]] = []
    for row_id, raw in conn.execute(
        "SELECT id, raw FROM events WHERE dedup_key IS NULL ORDER BY id ASC"
    ):
        try:
            record = json.loads(raw)
        except json.JSONDecodeError:
            continue
        dedup_key = _github_dedup_key(record)
        if dedup_key and dedup_key not in existing_keys:
            updates.append((dedup_key, row_id))
            existing_keys.add(dedup_key)
    if updates:
        conn.executemany("UPDATE events SET dedup_key = ? WHERE id = ?", updates)


def _ensure_schema(conn: sqlite3.Connection) -> None:
    """Initialize or migrate schema.

    - Creates the events table with dedup_key column if it does not exist.
    - Adds dedup_key column to pre-#307 databases via ALTER TABLE.
    - Backfills missing GitHub dedup keys from stored raw records.
    - Creates a partial UNIQUE index on non-NULL dedup_key values.
    """
    conn.executescript(_CREATE_TABLE_DDL)
    cols = {row[1] for row in conn.execute("PRAGMA table_info(events)")}
    if "dedup_key" not in cols:
        conn.executescript("ALTER TABLE events ADD COLUMN dedup_key TEXT;")
    _backfill_dedup_keys(conn)
    conn.executescript(_DEDUP_INDEX_DDL)


def append_sqlite(db_path: Path, record: Dict[str, Any]) -> Literal["saved", "skipped"]:
    """Insert record into SQLite DB.

    Returns 'saved' when the row is newly inserted.
    Returns 'skipped' when a row with the same dedup_key already exists
    (duplicate GitHub event).  Non-GitHub records (dedup_key=None) are
    always saved because SQLite treats each NULL as distinct.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    dedup_key = _github_dedup_key(record)
    with sqlite3.connect(str(db_path)) as conn:
        _ensure_schema(conn)
        cursor = conn.execute(
            "INSERT OR IGNORE INTO events (ts, domain, kind, dedup_key, raw)"
            " VALUES (?, ?, ?, ?, ?)",
            (
                record.get("ts"),
                record.get("domain"),
                record.get("kind"),
                dedup_key,
                json.dumps(record, ensure_ascii=False),
            ),
        )
        conn.commit()
    return "saved" if cursor.rowcount == 1 else "skipped"


def read_sqlite(db_path: Path) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT raw FROM events ORDER BY id ASC")
        for (raw,) in rows:
            out.append(json.loads(raw))
    return out
