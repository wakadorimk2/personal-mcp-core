from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

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


def _is_display_population_record(record: Dict[str, Any]) -> bool:
    if record.get("domain") == "summary":
        return False
    return record.get("source") != "web-form-ui"


def _is_scale_population_record(
    record: Dict[str, Any], boundary_date: Optional[str] = None
) -> bool:
    """Return True for future scale-only consumers.

    Issue #332 introduces a metadata contract and an aggregation seam only.
    Shipped `/api/heatmap` and `/api/heatmap/debug` semantics do not change here.
    A future scale-specific consumer may pass an explicit boundary date to opt
    into a narrower calibration window without changing display_population.
    """
    if not _is_display_population_record(record):
        return False
    if boundary_date is None:
        return True
    local_day = _local_date(record.get("ts", ""))
    return bool(local_day and local_day >= boundary_date)


def _count_events_by_date_filtered(
    rows: List[Dict[str, Any]],
    days: int,
    include_record: Callable[[Dict[str, Any]], bool],
) -> List[Dict[str, Any]]:
    """Count records by local day using an explicit population predicate."""
    if days <= 0:
        return []

    today = datetime.now().astimezone().date()
    buckets: Dict[str, int] = {}
    for i in range(days - 1, -1, -1):
        buckets[(today - timedelta(days=i)).isoformat()] = 0

    for record in rows:
        if not include_record(record):
            continue
        local_day = _local_date(record.get("ts", ""))
        if local_day and local_day in buckets:
            buckets[local_day] += 1

    return [{"date": day, "count": buckets[day]} for day in sorted(buckets)]


def _count_events_by_date_debug_from_rows(
    rows: List[Dict[str, Any]],
    days: int,
) -> List[Dict[str, Any]]:
    if days <= 0:
        return []

    today = datetime.now().astimezone().date()
    raw_buckets: Dict[str, int] = {}
    telemetry_buckets: Dict[str, int] = {}
    for i in range(days - 1, -1, -1):
        day = (today - timedelta(days=i)).isoformat()
        raw_buckets[day] = 0
        telemetry_buckets[day] = 0

    for record in rows:
        if record.get("domain") == "summary":
            continue
        day = _local_date(record.get("ts", ""))
        if day and day in raw_buckets:
            raw_buckets[day] += 1
            if record.get("source") == "web-form-ui":
                telemetry_buckets[day] += 1

    result: List[Dict[str, Any]] = []
    for day in sorted(raw_buckets):
        raw_count = raw_buckets[day]
        telemetry_count = telemetry_buckets[day]
        shipped_density = raw_count - telemetry_count
        result.append(
            {
                "date": day,
                "raw_count": raw_count,
                "shipped_density": shipped_density,
                "telemetry_count": telemetry_count,
                "life_count": shipped_density,
            }
        )
    return result


def _earliest_real_data_day(rows: List[Dict[str, Any]]) -> Optional[str]:
    days = [
        local_day
        for record in rows
        if record.get("domain") != "summary"
        for local_day in [_local_date(record.get("ts", ""))]
        if local_day
    ]
    if not days:
        return None
    return min(days)


def _percentile(sorted_values: List[int], percentile: int) -> Optional[float]:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return float(sorted_values[0])

    rank = (len(sorted_values) - 1) * percentile / 100
    low = int(rank)
    high = min(low + 1, len(sorted_values) - 1)
    return sorted_values[low] + (sorted_values[high] - sorted_values[low]) * (rank - low)


def _normalize_number(value: Optional[float], *, digits: int = 3) -> Optional[float | int]:
    if value is None:
        return None
    rounded = round(value, digits)
    if float(rounded).is_integer():
        return int(rounded)
    return rounded


def _density_stats(debug_rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts = [row["shipped_density"] for row in debug_rows]
    sorted_counts = sorted(counts)
    total_days = len(sorted_counts)
    zero_days = sum(1 for count in sorted_counts if count == 0)
    p75 = _percentile(sorted_counts, 75)
    p90 = _percentile(sorted_counts, 90)
    p95 = _percentile(sorted_counts, 95)
    max_count = sorted_counts[-1] if sorted_counts else None

    return {
        "total_days": total_days,
        "zero_days": zero_days,
        "zero_day_ratio": _normalize_number(
            zero_days / total_days if total_days else None,
            digits=4,
        ),
        "min": sorted_counts[0] if sorted_counts else None,
        "p50": _normalize_number(_percentile(sorted_counts, 50)),
        "p75": _normalize_number(p75),
        "p90": _normalize_number(p90),
        "p95": _normalize_number(p95),
        "max": max_count,
    }


def _heuristic_flags(stats: Dict[str, Any]) -> Dict[str, Any]:
    p75 = stats.get("p75")
    p90 = stats.get("p90")
    p95 = stats.get("p95")
    max_count = stats.get("max")

    p95_over_p75 = None
    if p75 not in (None, 0) and p95 is not None:
        p95_over_p75 = _normalize_number(float(p95) / float(p75), digits=2)

    max_over_p90 = None
    if p90 not in (None, 0) and max_count is not None:
        max_over_p90 = _normalize_number(float(max_count) / float(p90), digits=2)

    return {
        "advisory_only": True,
        "rules": {
            "p95_over_p75": {
                "value": p95_over_p75,
                "threshold": 3,
                "triggered": bool(p95_over_p75 is not None and p95_over_p75 >= 3),
                "note": "Upper-tail stretch signal only; not a decision rule.",
            },
            "max_over_p90": {
                "value": max_over_p90,
                "threshold": 5,
                "triggered": bool(max_over_p90 is not None and max_over_p90 >= 5),
                "note": "Single-day spike signal only; not a decision rule.",
            },
        },
    }


def _build_density_audit_window(
    *,
    label: str,
    role: str,
    debug_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    stats = _density_stats(debug_rows)
    return {
        "label": label,
        "role": role,
        "start_date": debug_rows[0]["date"] if debug_rows else None,
        "end_date": debug_rows[-1]["date"] if debug_rows else None,
        "stats": stats,
        "heuristic_flags": _heuristic_flags(stats),
    }


def heatmap_density_audit(
    primary_days: int = 365,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a scale-audit summary for shipped heatmap density.

    Maintainer policy for Issue #354:
    - primary conclusions come from the last 365 days by default
    - all-time (from earliest real data) is secondary context only
    - heuristic outlier flags are advisory, not normative
    """
    rows = read_events(data_dir=data_dir)
    primary_debug = _count_events_by_date_debug_from_rows(rows, primary_days)
    earliest_day = _earliest_real_data_day(rows)

    all_time_reference: Optional[Dict[str, Any]] = None
    if earliest_day is not None:
        today = datetime.now().astimezone().date()
        start_day = datetime.strptime(earliest_day, "%Y-%m-%d").date()
        all_time_days = (today - start_day).days + 1
        all_time_debug = _count_events_by_date_debug_from_rows(rows, all_time_days)
        all_time_reference = _build_density_audit_window(
            label="all_time_from_earliest_real_data",
            role="secondary_reference",
            debug_rows=all_time_debug,
        )

    return {
        "policy": {
            "primary_window_days": primary_days,
            "primary_conclusion_basis": "last_365_days" if primary_days == 365 else "last_n_days",
            "all_time_role": "secondary_reference_only",
            "heuristic_flags_role": "advisory_only",
        },
        "earliest_real_data_date": earliest_day,
        "primary_window": _build_density_audit_window(
            label=f"last_{primary_days}_days",
            role="primary_conclusion",
            debug_rows=primary_debug,
        ),
        "all_time_reference": all_time_reference,
    }


def count_events_by_date(days: int = 28, data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return [{date, count}] for the last `days` local days (0-count days included).

    The returned ``count`` is ``shipped_density`` as defined in
    ``docs/heatmap-state-density-spec.md`` Section 3 (Issue #312 / #317):

        shipped_density[date] = count(events WHERE
            local_date(ts) == date
            AND domain != "summary"
            AND source != "web-form-ui"
        )

    Excluded per observation layer (Section 2):
    - ``domain == "summary"``: derived data (daily summary artifacts)
    - ``source == "web-form-ui"``: UI telemetry (system-generated, weight 0)

    The ``weight 0 (exclude)`` decision and its rationale are in Section 4 of the
    spec. debug surface (``raw_count`` / ``telemetry_count``) is #256 scope;
    color scale is #257 scope — both are out of scope for #317.
    """
    rows = read_events(data_dir=data_dir)
    return _count_events_by_date_filtered(rows, days, _is_display_population_record)


def count_events_by_date_debug(
    days: int = 28, data_dir: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Return a debug-only per-day heatmap breakdown for verification.

    Fields per entry:
    - date: local YYYY-MM-DD, matching `/api/heatmap`
    - raw_count: all non-summary events for the day
    - shipped_density: current `/api/heatmap` count after telemetry exclusion
    - telemetry_count: events emitted by the web UI telemetry layer
    - life_count: raw_count minus telemetry_count
    """
    rows = read_events(data_dir=data_dir)
    return _count_events_by_date_debug_from_rows(rows, days)


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
