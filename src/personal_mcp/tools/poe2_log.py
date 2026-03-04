# src/personal_mcp/tools/poe2_log.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.storage.jsonl import append_jsonl, read_jsonl
from personal_mcp.storage.path import resolve_data_dir


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_since(since: Optional[str]) -> Optional[datetime]:
    if not since:
        return None
    # Accept "YYYY-MM-DD" or ISO
    if len(since) == 10 and since[4] == "-" and since[7] == "-":
        return datetime.fromisoformat(since + "T00:00:00+00:00")
    return datetime.fromisoformat(since)


@dataclass
class Poe2Log:
    ts: str
    kind: str
    text: str
    tags: List[str]
    meta: Dict[str, Any]


def log_add(
    text: str,
    kind: str = "note",
    tags: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    data_dir: Optional[str] = None,
) -> Poe2Log:
    record = Poe2Log(
        ts=_now_iso(),
        kind=kind,
        text=text.strip(),
        tags=tags or [],
        meta=meta or {},
    )

    data_dir = resolve_data_dir(data_dir)
    path = Path(data_dir) / "poe2" / "logs.jsonl"
    append_jsonl(path, asdict(record))
    return record


def log_list(
    n: int = 20,
    kind: Optional[str] = None,
    tag: Optional[str] = None,
    since: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    data_dir = resolve_data_dir(data_dir)
    path = Path(data_dir) / "poe2" / "logs.jsonl"
    rows = read_jsonl(path)

    since_dt = _parse_since(since)

    def ok(r: Dict[str, Any]) -> bool:
        if kind and r.get("kind") != kind:
            return False
        if tag and tag not in (r.get("tags") or []):
            return False
        if since_dt:
            ts = r.get("ts")
            if not ts:
                return False
            try:
                ts_dt = datetime.fromisoformat(ts)
            except Exception:
                return False
            if ts_dt < since_dt:
                return False
        return True

    filtered = [r for r in rows if ok(r)]
    return list(reversed(filtered))[: max(0, n)]
