from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.storage.jsonl import append_jsonl, read_jsonl
from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import append_sqlite, read_sqlite

PRIMARY_STORAGE = "events.db"
COMPAT_STORAGE = "events.jsonl"


def _paths(data_dir: Optional[str]) -> tuple[Path, Path]:
    resolved = Path(resolve_data_dir(data_dir))
    return resolved / PRIMARY_STORAGE, resolved / COMPAT_STORAGE


def append_event(record: Dict[str, Any], data_dir: Optional[str] = None) -> None:
    """Write an event to primary storage and compatibility storage."""
    db_path, jsonl_path = _paths(data_dir)
    append_sqlite(db_path, record)
    append_jsonl(jsonl_path, record)


def read_events(data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read from primary storage first, then fallback to compatibility storage."""
    db_path, jsonl_path = _paths(data_dir)
    rows = read_sqlite(db_path)
    if rows:
        return rows
    return read_jsonl(jsonl_path)
