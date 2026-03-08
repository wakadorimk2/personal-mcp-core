from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pytest

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.sqlite import append_sqlite
from personal_mcp.tools.candidates import (
    FIXED_CANDIDATES,
    MAX_CANDIDATE_LENGTH,
    _shorten_text,
    list_candidates,
)


def _ts(days_ago: int, seq: int) -> str:
    base = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return (base.replace(microsecond=0) + timedelta(seconds=seq)).isoformat()


def _add_event(
    db_path: Path,
    *,
    text: str,
    days_ago: int = 0,
    seq: int = 0,
    domain: str = "general",
    kind: str = "note",
) -> None:
    record = build_v1_record(
        ts=_ts(days_ago, seq),
        domain=domain,
        text=text,
        tags=[],
        kind=kind,
        source="test",
    )
    append_sqlite(db_path, record)


def _norm(text: str) -> str:
    return text.strip().lower()


def _sources(items: List[Dict[str, str]]) -> List[str]:
    return [x["source"] for x in items]


def _make_handler_for_test(data_dir: str):
    from personal_mcp.adapters.http_server import _make_handler

    return _make_handler(data_dir)


def _new_handler(handler_cls, path: str):
    handler = handler_cls.__new__(handler_cls)
    handler.headers = {}
    handler.rfile = io.BytesIO(b"")
    handler.wfile = io.BytesIO()
    handler.path = path
    handler.request_version = "HTTP/1.1"
    return handler


def _do_get_json(handler_cls, path: str) -> List[Tuple[int, Any]]:
    handler = _new_handler(handler_cls, path)
    responses: List[Tuple[int, Any]] = []
    handler._json = lambda status, body: responses.append((status, body))
    handler.do_GET()
    return responses


def test_list_candidates_cold_start_returns_fixed_only(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    for i in range(6):
        _add_event(db_path, text=f"event-{i}", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    expected = [{"text": t, "source": "fixed"} for t in FIXED_CANDIDATES]
    assert got == expected


@pytest.mark.parametrize("count", [7, 8])
def test_list_candidates_threshold_7_and_8_enable_non_fixed_sources(
    data_dir: Path, count: int
) -> None:
    db_path = data_dir / "events.db"
    for i in range(count):
        _add_event(db_path, text=f"log-{i}", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    assert any(item["source"] != "fixed" for item in got)


def test_list_candidates_dedup_prefers_higher_priority_source(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    texts = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta", "  休憩  "]
    for i, text in enumerate(texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    rest_items = [item for item in got if _norm(item["text"]) == "休憩"]
    assert len(rest_items) == 1
    assert rest_items[0]["source"] == "recent"


def test_list_candidates_can_include_today_frequent_source(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, text="today-only", seq=1)
    _add_event(db_path, text="today-only", seq=2)
    for i in range(3, 13):
        _add_event(db_path, text="recent-repeat", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    today_only = [item for item in got if item["text"] == "today-only"]
    assert len(today_only) == 1
    assert today_only[0]["source"] == "today_frequent"


def test_list_candidates_can_include_7d_frequent_source(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, text="week-only", days_ago=2, seq=1)
    _add_event(db_path, text="week-only", days_ago=2, seq=2)
    for i in range(3, 14):
        _add_event(db_path, text="today-repeat", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    week_only = [item for item in got if item["text"] == "week-only"]
    assert len(week_only) == 1
    assert week_only[0]["source"] == "7d_frequent"


def test_list_candidates_caps_at_8(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    for i in range(20):
        _add_event(db_path, text=f"event-{i:02d}", seq=i)

    got = list_candidates(data_dir=str(data_dir))
    assert len(got) == 8
    assert _sources(got) == ["recent"] * 8


def test_http_get_candidates_200(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    for i in range(8):
        _add_event(db_path, text=f"event-{i}", seq=i)

    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _do_get_json(handler_cls, "/api/candidates")
    assert len(responses) == 1
    status, body = responses[0]
    assert status == 200
    assert isinstance(body, list)
    assert len(body) <= 8
    assert all("text" in item and "source" in item for item in body)


# --- _shorten_text unit tests ---


def test_shorten_text_short_text_unchanged() -> None:
    assert _shorten_text("作業開始") == "作業開始"
    assert _shorten_text("休憩") == "休憩"
    assert _shorten_text("") == ""


def test_shorten_text_at_boundary_unchanged() -> None:
    text = "a" * MAX_CANDIDATE_LENGTH
    assert _shorten_text(text) == text


def test_shorten_text_long_text_within_limit() -> None:
    long_text = "あいうえおかきくけこさしすせそ"  # 15 chars
    result = _shorten_text(long_text)
    assert len(result) <= MAX_CANDIDATE_LENGTH


def test_shorten_text_splits_on_japanese_delimiter() -> None:
    assert _shorten_text("作業開始：朝のタスク確認") == "作業開始"
    assert _shorten_text("コーディング 詳細な説明が続く") == "コーディング"
    assert _shorten_text("移動。買い物をした") == "移動"


def test_shorten_text_splits_on_arrow() -> None:
    result = _shorten_text("作業開始→タスク管理の確認")
    assert result == "作業開始"
    assert len(result) <= MAX_CANDIDATE_LENGTH


# --- integration: long-text events produce short candidates ---


def test_list_candidates_long_events_produce_short_candidates(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    long_texts = [
        "今日の作業をしっかりと開始しました",
        "昼休みの後に作業を再開した記録",
        "移動中にメモしておく内容です",
        "コードレビューを実施しました",
        "夕方の振り返りをしています",
        "明日のタスクを整理した",
        "会議の準備をしていた",
        "設計について検討した",
        "ドキュメントを更新しました",
        "テストを書いていた",
    ]
    for i, text in enumerate(long_texts):
        _add_event(db_path, text=text, seq=i)

    got = list_candidates(data_dir=str(data_dir))
    non_fixed = [item for item in got if item["source"] != "fixed"]

    assert non_fixed, "long-text events should produce at least one non-fixed candidate"
    assert all(
        len(item["text"]) <= MAX_CANDIDATE_LENGTH for item in non_fixed
    ), f"all non-fixed candidates must be <= {MAX_CANDIDATE_LENGTH} chars: {non_fixed}"
