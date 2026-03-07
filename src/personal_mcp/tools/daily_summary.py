from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import append_sqlite, read_sqlite


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_date(ts_str: str) -> Optional[str]:
    try:
        ts_dt = datetime.fromisoformat(ts_str)
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        return ts_dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
    except Exception:
        return None


def _events_for_date(rows: List[Dict[str, Any]], date: str) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    for r in rows:
        if r.get("domain") == "summary":
            continue
        ts_str = r.get("ts", "")
        if _utc_date(ts_str) == date:
            result.append(r)
    return result


def _build_fact_text(events: List[Dict[str, Any]]) -> str:
    if not events:
        return "(記録なし)"
    by_domain: Dict[str, List[str]] = {}
    for r in events:
        domain = r.get("domain", "unknown")
        text = r.get("data", {}).get("text", "")
        by_domain.setdefault(domain, []).append(text)

    parts = []
    for domain in sorted(by_domain):
        texts = [t for t in by_domain[domain] if t]
        count = len(by_domain[domain])
        sample = texts[0] if texts else ""
        if count > 1:
            parts.append(f"{domain}: {sample} 他{count - 1}件")
        else:
            parts.append(f"{domain}: {sample}")
    return " / ".join(parts)


def get_latest_summary(date: str, data_dir: Optional[str] = None) -> Optional[Dict[str, Any]]:
    db_path = Path(resolve_data_dir(data_dir)) / "events.db"
    latest: Optional[Dict[str, Any]] = None
    for r in read_sqlite(db_path):
        if r.get("domain") == "summary" and r.get("data", {}).get("date") == date:
            latest = r
    return latest


def generate_daily_summary(
    date: str,
    *,
    annotation: Optional[str] = None,
    interpretation: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    db_path = Path(resolve_data_dir(data_dir)) / "events.db"
    events = _events_for_date(read_sqlite(db_path), date)
    extra: Dict[str, Any] = {"date": date}
    if annotation:
        extra["annotation"] = annotation
    if interpretation:
        extra["interpretation"] = interpretation

    record = build_v1_record(
        ts=_now_iso(),
        domain="summary",
        text=_build_fact_text(events),
        tags=[],
        kind="artifact",
        source="generated",
        extra_data=extra,
    )
    append_sqlite(db_path, record)
    return record
