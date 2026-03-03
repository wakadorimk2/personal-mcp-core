# src/personal_mcp/tools/event.py
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.core.event import ALLOWED_DOMAINS, Event
from personal_mcp.storage.jsonl import append_jsonl, read_jsonl


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_since(since: Optional[str]) -> Optional[datetime]:
    """Parse --since value to a timezone-aware datetime.

    "YYYY-MM-DD" is treated as UTC midnight (start of that day in UTC).
    ISO datetime strings are parsed as-is (must include timezone offset).
    """
    if not since:
        return None
    if len(since) == 10 and since[4] == "-" and since[7] == "-":
        return datetime.fromisoformat(since + "T00:00:00+00:00")
    return datetime.fromisoformat(since)


def event_add(
    domain: str,
    text: str,
    tags: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    data_dir: str = "data",
) -> Dict[str, Any]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"unsupported domain: {domain}")

    payload: Dict[str, Any] = {"text": text}
    if meta:
        payload["meta"] = meta

    event = Event(
        ts=_now_iso(),
        domain=domain,
        payload=payload,
        tags=tags or [],
    )

    path = Path(data_dir) / "events.jsonl"
    record = asdict(event)
    append_jsonl(path, record)
    return record


def event_list(
    n: int = 20,
    domain: Optional[str] = None,
    date: Optional[str] = None,
    since: Optional[str] = None,
    data_dir: str = "data",
) -> List[Dict[str, Any]]:
    """Return filtered events, newest first, limited to n records.

    --domain: include only events matching this domain string.
    --date:   include only events whose local date equals YYYY-MM-DD.
    --since:  earliest timestamp (inclusive). "YYYY-MM-DD" means UTC midnight of
              that date; ISO datetime strings are used as-is.
    --n:      after all filters, return the newest n records (newest first).

    events.jsonl が存在しない場合は空リストを返す（書き込みは一切しない）。
    """
    path = Path(data_dir) / "events.jsonl"
    rows = read_jsonl(path)

    since_dt = _parse_since(since)

    def ok(r: Dict[str, Any]) -> bool:
        if domain and r.get("domain") != domain:
            return False
        ts_str = r.get("ts")
        if not ts_str:
            return True
        try:
            ts_dt = datetime.fromisoformat(ts_str)
            if ts_dt.tzinfo is None:
                ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        except Exception:
            return True
        if since_dt and ts_dt < since_dt:
            return False
        if date:
            local_date = ts_dt.astimezone().strftime("%Y-%m-%d")
            if local_date != date:
                return False
        return True

    filtered = [r for r in rows if ok(r)]
    # newest first, then take up to n records
    return list(reversed(filtered))[: max(0, n)]
