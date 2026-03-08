from __future__ import annotations

import io
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.sqlite import append_sqlite
from personal_mcp.tools.daily_summary import (
    count_events_by_date,
    generate_daily_summary,
    list_summaries,
)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _date_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def _date_days_after(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def _add_event(db_path: Path, domain: str = "mood", ts: str | None = None) -> None:
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    record = build_v1_record(ts=ts, domain=domain, text="x", tags=[], kind="note", source="test")
    append_sqlite(db_path, record)


def _append_summary(db_path: Path, date_str: str, text: str = "summary") -> None:
    record = build_v1_record(
        ts=datetime.now(timezone.utc).isoformat(),
        domain="summary",
        text=text,
        tags=[],
        kind="artifact",
        source="generated",
        extra_data={"date": date_str},
    )
    append_sqlite(db_path, record)


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


def _do_get_html(handler_cls, path: str) -> Tuple[List[int], Dict[str, str], str]:
    handler = _new_handler(handler_cls, path)
    statuses: List[int] = []
    headers: Dict[str, str] = {}
    handler.send_response = lambda status: statuses.append(status)
    handler.send_header = lambda k, v: headers.__setitem__(k, v)
    handler.end_headers = lambda: None
    handler.do_GET()
    return statuses, headers, handler.wfile.getvalue().decode("utf-8")


def test_count_events_by_date_returns_28_entries(data_dir: Path) -> None:
    result = count_events_by_date(28, data_dir=str(data_dir))
    assert len(result) == 28


def test_count_events_by_date_all_zero_when_empty(data_dir: Path) -> None:
    result = count_events_by_date(28, data_dir=str(data_dir))
    assert all(item["count"] == 0 for item in result)


def test_count_events_by_date_counts_today_events(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, domain="mood")
    _add_event(db_path, domain="eng")
    result = count_events_by_date(28, data_dir=str(data_dir))
    today_entry = next(r for r in result if r["date"] == _today_utc())
    assert today_entry["count"] == 2


def test_count_events_by_date_excludes_summary_domain(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _append_summary(db_path, _today_utc())
    result = count_events_by_date(28, data_dir=str(data_dir))
    today_entry = next(r for r in result if r["date"] == _today_utc())
    assert today_entry["count"] == 0


def test_count_events_by_date_excludes_old_events(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, ts=_date_days_ago(100) + "T12:00:00+00:00")
    result = count_events_by_date(28, data_dir=str(data_dir))
    assert all(item["count"] == 0 for item in result)


def test_count_events_by_date_sorted_ascending(data_dir: Path) -> None:
    result = count_events_by_date(28, data_dir=str(data_dir))
    dates = [item["date"] for item in result]
    assert dates == sorted(dates)


def test_list_summaries_empty_when_no_summaries(data_dir: Path) -> None:
    assert list_summaries(28, data_dir=str(data_dir)) == []


def test_list_summaries_newest_first(data_dir: Path) -> None:
    generate_daily_summary(_date_days_ago(2), data_dir=str(data_dir))
    generate_daily_summary(_date_days_ago(1), data_dir=str(data_dir))
    result = list_summaries(28, data_dir=str(data_dir))
    dates = [r["date"] for r in result]
    assert dates == sorted(dates, reverse=True)


def test_list_summaries_excludes_old_dates(data_dir: Path) -> None:
    old_date = _date_days_ago(100)
    generate_daily_summary(old_date, data_dir=str(data_dir))
    result = list_summaries(28, data_dir=str(data_dir))
    assert not any(r["date"] == old_date for r in result)


def test_list_summaries_excludes_future_dates(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    today = _today_utc()
    future = _date_days_after(1)
    _append_summary(db_path, today, text="today")
    _append_summary(db_path, future, text="future")
    result = list_summaries(28, data_dir=str(data_dir))
    assert [r["date"] for r in result] == [today]


def test_list_summaries_includes_annotation_and_interpretation(data_dir: Path) -> None:
    today = _today_utc()
    generate_daily_summary(today, annotation="注釈", interpretation="解釈", data_dir=str(data_dir))
    result = list_summaries(28, data_dir=str(data_dir))
    assert len(result) == 1
    assert result[0]["annotation"] == "注釈"
    assert result[0]["interpretation"] == "解釈"


def test_list_summaries_omits_annotation_key_when_absent(data_dir: Path) -> None:
    generate_daily_summary(_today_utc(), data_dir=str(data_dir))
    result = list_summaries(28, data_dir=str(data_dir))
    assert "annotation" not in result[0]
    assert "interpretation" not in result[0]


def test_http_get_dashboard_200(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    statuses, headers, html = _do_get_html(handler_cls, "/dashboard")
    assert statuses == [200]
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert "直近28日" in html
    assert 'id="heatmap"' in html
    assert 'id="refresh-btn"' in html
    assert "再読み込みに失敗しました。再試行してください。" in html


def test_http_get_root_returns_dashboard_html(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _, _, root_html = _do_get_html(handler_cls, "/")
    _, _, dashboard_html = _do_get_html(handler_cls, "/dashboard")
    assert root_html == dashboard_html
    assert 'id="heatmap"' in root_html


def test_http_get_index_html_returns_dashboard_html(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _, _, index_html = _do_get_html(handler_cls, "/index.html")
    _, _, dashboard_html = _do_get_html(handler_cls, "/dashboard")
    assert index_html == dashboard_html
    assert 'id="heatmap"' in index_html


def test_http_get_input_returns_legacy_log_form_html(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    statuses, headers, html = _do_get_html(handler_cls, "/input")
    assert statuses == [200]
    assert headers["Content-Type"] == "text/html; charset=utf-8"
    assert 'data-mode="quick"' in html
    assert 'id="suggestion"' in html
    assert 'id="heatmap"' not in html


def test_http_get_heatmap_200(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    resp = _do_get_json(handler_cls, "/api/heatmap")
    assert len(resp) == 1
    status, body = resp[0]
    assert status == 200
    assert len(body) == 28
    assert all("date" in item and "count" in item for item in body)


def test_http_get_summaries_list_200_empty(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    status, body = _do_get_json(handler_cls, "/api/summaries/list")[0]
    assert status == 200
    assert body == []


def test_http_get_summaries_list_200_with_record(data_dir: Path) -> None:
    today = _today_utc()
    generate_daily_summary(today, data_dir=str(data_dir))
    handler_cls = _make_handler_for_test(str(data_dir))
    status, body = _do_get_json(handler_cls, "/api/summaries/list")[0]
    assert status == 200
    assert len(body) == 1
    assert body[0]["date"] == today


def test_http_get_dashboard_layout_order(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _, _, html = _do_get_html(handler_cls, "/dashboard")
    heatmap_pos = html.find('id="heatmap"')
    candidates_pos = html.find('id="candidates"')
    log_text_pos = html.find('id="log-text"')
    assert heatmap_pos != -1
    assert candidates_pos != -1
    assert log_text_pos != -1
    assert heatmap_pos < candidates_pos < log_text_pos


def test_http_get_dashboard_candidate_tap_script_exists(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _, _, html = _do_get_html(handler_cls, "/dashboard")
    assert "var text = candidateText(item);" in html
    assert "tag.dataset.source = source;" in html
    assert "input.value = text;" in html
    assert 'await fetch("/api/candidates")' in html
