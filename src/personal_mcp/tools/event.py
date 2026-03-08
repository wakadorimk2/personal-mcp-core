# src/personal_mcp/tools/event.py
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from personal_mcp.core.event import ALLOWED_DOMAINS, build_v1_record
from personal_mcp.storage.events_store import append_event, read_events


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
    kind: Optional[str] = None,
    tags: Optional[List[str]] = None,
    meta: Optional[Dict[str, Any]] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"unsupported domain: {domain}")

    meta = meta or {}
    source = meta.get("source")
    ref = meta.get("ref")
    extra_data = {k: v for k, v in meta.items() if k not in {"source", "ref"}}

    record = build_v1_record(
        ts=_now_iso(),
        domain=domain,
        text=text,
        tags=tags or [],
        kind=kind,
        source=source,
        ref=ref,
        extra_data=extra_data or None,
    )
    append_event(record, data_dir=data_dir)
    return record


def event_list(
    n: int = 20,
    domain: Optional[str] = None,
    date: Optional[str] = None,
    since: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return filtered events, newest first, limited to n records.

    --domain: include only events matching this domain string.
    --date:   include only events whose local date equals YYYY-MM-DD.
    --since:  earliest timestamp (inclusive). "YYYY-MM-DD" means UTC midnight of
              that date; ISO datetime strings are used as-is.
    --n:      after all filters, return the newest n records (newest first).

    primary が空の場合は互換経路を読む。どちらもなければ空配列を返す。
    """
    rows = read_events(data_dir=data_dir)

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
