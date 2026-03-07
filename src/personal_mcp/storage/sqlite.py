from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

_DDL = """
CREATE TABLE IF NOT EXISTS events (
    id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ts     TEXT NOT NULL,
    domain TEXT NOT NULL,
    kind   TEXT,
    raw    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
CREATE INDEX IF NOT EXISTS idx_events_domain ON events (domain);
"""


def append_sqlite(db_path: Path, record: Dict[str, Any]) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(_DDL)
        conn.execute(
            "INSERT INTO events (ts, domain, kind, raw) VALUES (?, ?, ?, ?)",
            (
                record.get("ts"),
                record.get("domain"),
                record.get("kind"),
                json.dumps(record, ensure_ascii=False),
            ),
        )
        conn.commit()


def read_sqlite(db_path: Path) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT raw FROM events ORDER BY id ASC")
        for (raw,) in rows:
            out.append(json.loads(raw))
    return out
