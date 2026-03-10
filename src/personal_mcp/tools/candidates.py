from __future__ import annotations

import re
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import read_sqlite

try:
    from fugashi import Tagger
except ImportError:  # pragma: no cover - exercised via fallback path in tests
    Tagger = None

MAX_CANDIDATES = 8
MAX_CANDIDATES_PER_TEXT = 2
RECENT_SOURCE_LIMIT = 10
COLD_START_THRESHOLD = 7
MAX_CANDIDATE_LENGTH = 10
_SHORTEN_SPLIT = re.compile(r"[\s\u3000。、・：→←「」【】（）\[\]/|]+")
_TRAILING_NOISE = re.compile(r"[~〜!！?？]+$")
_ALNUM = re.compile(r"[A-Za-z0-9]")
_ASCII_SLUG = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
_ASCII_WORD = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_KATAKANA = re.compile(r"^[ァ-ヶー]+$")
_HONORIFICS = frozenset({"さん", "ちゃん", "くん", "君", "氏", "様", "先生"})
_CANDIDATE_STOPWORDS = frozenset(
    {
        "今日",
        "明日",
        "昨日",
        "今",
        "朝",
        "昼",
        "夜",
        "夕方",
        "記録",
        "内容",
        "こと",
        "もの",
        # These verbal nouns tend to appear as low-signal follow-up candidates
        # after a more descriptive first label and can crowd out natural labels.
        "消費",
        "実施",
        "調査",
    }
)
_CANDIDATE_POS2 = frozenset({"普通名詞", "固有名詞", "数詞"})
_tagger: Optional[Any] = None
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


def _shorten_text(text: str) -> str:
    """Trim a log sentence to a short tag-like label for mobile display."""
    text = text.strip()
    if not text:
        return text
    parts = [p for p in _SHORTEN_SPLIT.split(text) if p.strip()]
    if parts:
        text = parts[0].strip()
    return text[:MAX_CANDIDATE_LENGTH]


def _clean_candidate_text(text: str) -> str:
    text = _TRAILING_NOISE.sub("", text.strip())
    return text[:MAX_CANDIDATE_LENGTH]


def _is_sensitive_label(text: str) -> bool:
    return any(suffix in text for suffix in _HONORIFICS)


def _is_meaningful_candidate(text: str) -> bool:
    if not text:
        return False
    if text in _CANDIDATE_STOPWORDS:
        return False
    if text.isdigit():
        return False
    if _ASCII_SLUG.fullmatch(text) and len(text) <= 2 and text.islower():
        return False
    if len(text) == 1 and not (_ALNUM.search(text) or _KATAKANA.fullmatch(text)):
        return False
    return True


def _feature_attr(word: Any, name: str) -> str:
    feature = getattr(word, "feature", None)
    value = getattr(feature, name, "")
    if value in (None, "*"):
        return ""
    return str(value)


def _get_tagger() -> Optional[Any]:
    global _tagger
    if Tagger is None:
        return None
    if _tagger is None:
        try:
            _tagger = Tagger()
        except Exception:
            _tagger = False
    return _tagger or None


def _is_person_name(word: Any) -> bool:
    return _feature_attr(word, "pos2") == "固有名詞" and _feature_attr(word, "pos3") == "人名"


def _join_chunk_tokens(tokens: List[str]) -> str:
    parts: List[str] = []
    prev = ""
    for token in tokens:
        if parts and _ASCII_WORD.fullmatch(prev) and _ASCII_WORD.fullmatch(token):
            parts.append(" ")
        parts.append(token)
        prev = token
    return "".join(parts)


def _candidate_from_chunk(tokens: List[str]) -> str:
    if not tokens:
        return ""

    for size in range(len(tokens), 0, -1):
        for start in range(len(tokens) - size + 1):
            chunk = tokens[start : start + size]
            candidate = _join_chunk_tokens(chunk).strip()
            if not candidate:
                continue
            if len(candidate) > MAX_CANDIDATE_LENGTH:
                continue
            if _is_sensitive_label(candidate):
                continue
            if _is_meaningful_candidate(candidate):
                return candidate
    return ""


def _tokenized_candidates(text: str) -> tuple[List[str], bool]:
    tagger = _get_tagger()
    if tagger is None:
        return [], False

    try:
        words = list(tagger(text))
    except Exception:
        return [], False

    chunks: List[List[str]] = []
    current: List[str] = []
    sensitive_hit = False

    for idx, word in enumerate(words):
        surface = str(getattr(word, "surface", "")).strip()
        if not surface:
            continue

        pos1 = _feature_attr(word, "pos1")
        pos2 = _feature_attr(word, "pos2")
        next_surface = ""
        if idx + 1 < len(words):
            next_surface = str(getattr(words[idx + 1], "surface", "")).strip()

        if _is_person_name(word):
            sensitive_hit = True
            if current:
                chunks.append(current)
                current = []
            continue

        if next_surface in _HONORIFICS and pos1 == "名詞":
            sensitive_hit = True
            if current:
                chunks.append(current)
                current = []
            continue

        if pos1 == "名詞" and pos2 in _CANDIDATE_POS2 and surface not in _HONORIFICS:
            current.append(surface)
            continue

        if current:
            chunks.append(current)
            current = []

    if current:
        chunks.append(current)

    candidates: List[str] = []
    seen: set[str] = set()
    for chunk in chunks:
        candidate = _candidate_from_chunk(chunk)
        normalized = _normalize_text(candidate)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        candidates.append(candidate)
        if len(candidates) >= MAX_CANDIDATES_PER_TEXT:
            return candidates, sensitive_hit

    if candidates:
        return candidates, sensitive_hit
    if sensitive_hit:
        return [], True
    return [], False


def _extract_candidate_texts(text: str) -> List[str]:
    if _ASCII_SLUG.fullmatch(text.strip()):
        return [_clean_candidate_text(text)]

    tokenized, sensitive_hit = _tokenized_candidates(text)
    if tokenized:
        return tokenized
    if sensitive_hit:
        return []

    fallback = _clean_candidate_text(_shorten_text(text))
    if _is_sensitive_label(fallback):
        return []
    if _is_meaningful_candidate(fallback):
        return [fallback]
    return []


def _extract_candidate_text(text: str) -> str:
    candidates = _extract_candidate_texts(text)
    if candidates:
        return candidates[0]
    return ""


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
            for candidate in _extract_candidate_texts(text):
                normalized = _normalize_text(candidate)
                if not normalized or normalized in seen:
                    continue
                seen.add(normalized)
                merged.append({"text": candidate, "source": source_name})
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
