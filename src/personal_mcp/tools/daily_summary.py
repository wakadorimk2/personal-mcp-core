from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.events_store import append_event, read_events


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


def _local_date(ts_str: str) -> Optional[str]:
    try:
        ts_dt = datetime.fromisoformat(ts_str)
        if ts_dt.tzinfo is None:
            ts_dt = ts_dt.replace(tzinfo=timezone.utc)
        return ts_dt.astimezone().strftime("%Y-%m-%d")
    except Exception:
        return None


def _parse_iso_date(date_str: str) -> Optional[date]:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
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
    latest: Optional[Dict[str, Any]] = None
    for r in read_events(data_dir=data_dir):
        if r.get("domain") == "summary" and r.get("data", {}).get("date") == date:
            latest = r
    return latest


def count_events_by_date(days: int = 28, data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return [{date, count}] for the last `days` local days, including 0-count days.

    This is the current MVP feed for `/api/heatmap`: raw non-summary event counts.
    Heatmap semantics are defined separately in `docs/heatmap-state-density-spec.md`
    (Issue #253), and follow-up issues may replace this with a layer-aware aggregate.
    """
    if days <= 0:
        return []

    today = datetime.now().astimezone().date()
    buckets: Dict[str, int] = {}
    for i in range(days - 1, -1, -1):
        buckets[(today - timedelta(days=i)).isoformat()] = 0

    for r in read_events(data_dir=data_dir):
        if r.get("domain") == "summary":
            continue
        d = _local_date(r.get("ts", ""))
        if d and d in buckets:
            buckets[d] += 1

    return [{"date": d, "count": buckets[d]} for d in sorted(buckets)]


def list_summaries(days: int = 28, data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return latest summary per date for the last `days` days, newest first."""
    if days <= 0:
        return []

    today = datetime.now(timezone.utc).date()
    cutoff = today - timedelta(days=days - 1)

    by_date: Dict[str, Dict[str, Any]] = {}
    for r in read_events(data_dir=data_dir):
        if r.get("domain") != "summary":
            continue
        d_str = r.get("data", {}).get("date", "")
        d = _parse_iso_date(d_str)
        if d is None:
            continue
        if cutoff <= d <= today:
            by_date[d_str] = r

    result: List[Dict[str, Any]] = []
    for d_str in sorted(by_date, reverse=True):
        rec = by_date[d_str]
        data = rec.get("data", {})
        entry: Dict[str, Any] = {"date": d_str, "text": data.get("text", "")}
        if "annotation" in data:
            entry["annotation"] = data["annotation"]
        if "interpretation" in data:
            entry["interpretation"] = data["interpretation"]
        result.append(entry)
    return result


def generate_daily_summary(
    date: str,
    *,
    annotation: Optional[str] = None,
    interpretation: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    events = _events_for_date(read_events(data_dir=data_dir), date)
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
    append_event(record, data_dir=data_dir)
    return record
