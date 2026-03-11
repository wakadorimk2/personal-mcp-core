from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.storage.jsonl import read_jsonl
from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import append_sqlite, read_sqlite

PRIMARY_STORAGE = "events.db"
COMPAT_STORAGE = "events.jsonl"


def _paths(data_dir: Optional[str]) -> tuple[Path, Path]:
    resolved = Path(resolve_data_dir(data_dir))
    return resolved / PRIMARY_STORAGE, resolved / COMPAT_STORAGE


def append_event(record: Dict[str, Any], data_dir: Optional[str] = None) -> None:
    """Write an event to the runtime primary storage."""
    db_path, _ = _paths(data_dir)
    append_sqlite(db_path, record)


def read_events(data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Read events from the runtime primary storage only."""
    db_path, _ = _paths(data_dir)
    return read_sqlite(db_path)


def rebuild_jsonl_from_db(data_dir: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Regenerate compatibility JSONL from primary DB records."""
    db_path, jsonl_path = _paths(data_dir)
    if not db_path.exists():
        raise FileNotFoundError(f"missing source file: {db_path}")

    source_records = read_sqlite(db_path)
    target_records = read_jsonl(jsonl_path)
    result: Dict[str, Any] = {
        "direction": "db_to_jsonl",
        "dry_run": dry_run,
        "source_path": str(db_path),
        "target_path": str(jsonl_path),
        "source_count": len(source_records),
        "target_count": len(target_records),
        "count_diff": len(source_records) - len(target_records),
    }
    if dry_run:
        return result

    jsonl_path.parent.mkdir(parents=True, exist_ok=True)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for record in source_records:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    result["written_count"] = len(source_records)
    return result


def rebuild_db_from_jsonl(data_dir: Optional[str] = None, dry_run: bool = False) -> Dict[str, Any]:
    """Regenerate primary DB from compatibility JSONL records.

    Semantics: faithful reconstruction with no deduplication.
    All JSONL records are inserted as-is, so duplicate records in JSONL are
    preserved in the regenerated DB. Runtime dedup remains the responsibility
    of github_sync / github_ingest.
    """
    db_path, jsonl_path = _paths(data_dir)
    if not jsonl_path.exists():
        raise FileNotFoundError(f"missing source file: {jsonl_path}")

    source_records = read_jsonl(jsonl_path)
    target_records = read_sqlite(db_path)
    result: Dict[str, Any] = {
        "direction": "jsonl_to_db",
        "dry_run": dry_run,
        "source_path": str(jsonl_path),
        "target_path": str(db_path),
        "source_count": len(source_records),
        "target_count": len(target_records),
        "count_diff": len(source_records) - len(target_records),
    }
    if dry_run:
        return result

    if db_path.exists():
        db_path.unlink()
    for record in source_records:
        append_sqlite(db_path, record)
    result["written_count"] = len(source_records)
    return result
