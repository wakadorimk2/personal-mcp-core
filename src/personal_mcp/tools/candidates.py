from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import read_sqlite

MAX_CANDIDATES = 8
RECENT_SOURCE_LIMIT = 10
COLD_START_THRESHOLD = 7
FIXED_CANDIDATES: tuple[str, ...] = (
    "作業開始",
    "作業再開",
    "休憩",
    "食事",
    "移動",
    "作業完了",
    "振り返り",
    "就寝準備",
)


def _utc_date(ts_str: str) -> Optional[date]:
    try:
        ts = datetime.fromisoformat(ts_str)
    except Exception:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).date()


def _normalize_text(text: str) -> str:
    return text.strip().lower()


def _is_candidate_event(row: Dict[str, Any]) -> bool:
    if row.get("domain") == "summary":
        return False
    if row.get("kind") == "interaction":
        return False
    text = row.get("data", {}).get("text", "")
    return isinstance(text, str) and bool(text.strip())


def _event_text(row: Dict[str, Any]) -> str:
    text = row.get("data", {}).get("text", "")
    return text.strip() if isinstance(text, str) else ""


def _recent_texts(rows: List[Dict[str, Any]]) -> List[str]:
    recent = rows[-RECENT_SOURCE_LIMIT:]
    return [_event_text(r) for r in reversed(recent)]


def _frequent_texts(rows: List[Dict[str, Any]]) -> List[str]:
    if not rows:
        return []

    counter: Counter[str] = Counter()
    latest_idx: Dict[str, int] = {}
    latest_text: Dict[str, str] = {}

    for idx, row in enumerate(rows):
        text = _event_text(row)
        normalized = _normalize_text(text)
        if not normalized:
            continue
        counter[normalized] += 1
        latest_idx[normalized] = idx
        latest_text[normalized] = text

    ordered_keys = sorted(counter.keys(), key=lambda k: (-counter[k], -latest_idx[k], k))
    return [latest_text[k] for k in ordered_keys]


def _merge_sources(sources: List[tuple[str, List[str]]], limit: int) -> List[Dict[str, str]]:
    merged: List[Dict[str, str]] = []
    seen: set[str] = set()

    for source_name, texts in sources:
        for text in texts:
            normalized = _normalize_text(text)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            merged.append({"text": text.strip(), "source": source_name})
            if len(merged) >= limit:
                return merged
    return merged


def list_candidates(
    data_dir: Optional[str] = None, limit: int = MAX_CANDIDATES
) -> List[Dict[str, str]]:
    if limit <= 0:
        return []

    db_path = Path(resolve_data_dir(data_dir)) / "events.db"
    rows = [r for r in read_sqlite(db_path) if _is_candidate_event(r)]

    fixed = list(FIXED_CANDIDATES)
    if len(rows) < COLD_START_THRESHOLD:
        return _merge_sources([("fixed", fixed)], limit=min(limit, MAX_CANDIDATES))

    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=6)

    today_rows: List[Dict[str, Any]] = []
    week_rows: List[Dict[str, Any]] = []
    for row in rows:
        row_date = _utc_date(str(row.get("ts", "")))
        if row_date is None:
            continue
        if row_date == today:
            today_rows.append(row)
        if week_start <= row_date <= today:
            week_rows.append(row)

    sources = [
        ("recent", _recent_texts(rows)),
        ("today_frequent", _frequent_texts(today_rows)),
        ("7d_frequent", _frequent_texts(week_rows)),
        ("fixed", fixed),
    ]
    return _merge_sources(sources, limit=min(limit, MAX_CANDIDATES))
