from __future__ import annotations

import io
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.sqlite import append_sqlite
from personal_mcp.tools.candidates import FIXED_CANDIDATES
from personal_mcp.tools.daily_summary import (
    count_events_by_date,
    count_events_by_date_debug,
    generate_daily_summary,
    list_summaries,
)


def _today_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _today_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")


def _date_days_ago(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")


def _date_days_after(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).strftime("%Y-%m-%d")


def _add_event(db_path: Path, domain: str = "mood", ts: str | None = None) -> None:
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    record = build_v1_record(ts=ts, domain=domain, text="x", tags=[], kind="note", source="test")
    append_sqlite(db_path, record)


def _add_telemetry_event(db_path: Path, ts: str | None = None) -> None:
    """Add a UI telemetry event (source="web-form-ui") excluded by shipped_density."""
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    record = build_v1_record(
        ts=ts, domain="general", text="x", tags=[], kind="interaction", source="web-form-ui"
    )
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


def _add_telemetry_event(db_path: Path, ts: str | None = None) -> None:
    if ts is None:
        ts = datetime.now(timezone.utc).isoformat()
    record = build_v1_record(
        ts=ts,
        domain="general",
        text="[ui] input_submitted",
        tags=["ux", "experiment"],
        kind="interaction",
        source="web-form-ui",
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
    handler.requestline = f"GET {path} HTTP/1.1"
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


class _BrokenPipeWriter:
    def write(self, _payload: bytes) -> int:
        raise BrokenPipeError(32, "Broken pipe")


class _ConnectionResetWriter:
    def write(self, _payload: bytes) -> int:
        raise ConnectionResetError(104, "Connection reset by peer")


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
    today_entry = next(r for r in result if r["date"] == _today_local())
    assert today_entry["count"] == 2


def test_count_events_by_date_excludes_summary_domain(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _append_summary(db_path, _today_utc())
    result = count_events_by_date(28, data_dir=str(data_dir))
    today_entry = next(r for r in result if r["date"] == _today_local())
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


def test_count_events_by_date_excludes_web_form_ui_source(data_dir: Path) -> None:
    """Telemetry-only day: shipped_density == 0 (source="web-form-ui" excluded)."""
    db_path = data_dir / "events.db"
    _add_telemetry_event(db_path)
    result = count_events_by_date(28, data_dir=str(data_dir))
    today_entry = next(r for r in result if r["date"] == _today_local())
    assert today_entry["count"] == 0


def test_count_events_by_date_mixed_day_shipped_density(data_dir: Path) -> None:
    """Mixed day: telemetry + user-authored + summary → only user-authored counted.

    shipped_density = 2 (mood + eng)
    telemetry_count = 3 (web-form-ui, excluded per weight 0, #312/#317)
    summary excluded as domain="summary"
    """
    db_path = data_dir / "events.db"
    today_local = _today_local()
    # user-authored events — counted
    _add_event(db_path, domain="mood")
    _add_event(db_path, domain="eng")
    # UI telemetry events — excluded (source="web-form-ui")
    _add_telemetry_event(db_path)
    _add_telemetry_event(db_path)
    _add_telemetry_event(db_path)
    # summary artifact — excluded (domain="summary")
    _append_summary(db_path, today_local)
    result = count_events_by_date(28, data_dir=str(data_dir))
    today_entry = next(r for r in result if r["date"] == today_local)
    assert today_entry["count"] == 2


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
    assert 'id="draft-preview"' in html
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


def test_http_get_heatmap_returns_shipped_density_for_mixed_day(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    today_local = _today_local()
    _add_event(db_path, domain="mood")
    _add_event(db_path, domain="eng")
    _add_telemetry_event(db_path)
    _add_telemetry_event(db_path)
    _append_summary(db_path, today_local)

    handler_cls = _make_handler_for_test(str(data_dir))
    status, body = _do_get_json(handler_cls, "/api/heatmap")[0]

    assert status == 200
    today_entry = next(r for r in body if r["date"] == today_local)
    assert today_entry["count"] == 2


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
    assert 'id="candidate-compose-mode"' in html
    assert 'id="candidate-quick-mode"' in html
    assert 'id="candidate-mode-hint"' in html
    assert 'var candidateTapMode = "compose";' in html
    assert 'if (candidateTapMode === "quick") {' in html
    assert "await saveCandidateQuickLog(text, source);" in html
    assert 'setCandidateTapMode("quick");' in html
    assert "function setDashboardBusy(disabled) {" in html
    assert "tag.disabled = disabled;" in html
    assert 'trigger: "candidate_quick_save"' in html
    assert "var text = candidateText(item);" in html
    assert "tag.dataset.source = source;" in html
    assert "input.value = text;" in html
    assert "renderComposerState();" in html
    assert "var dashboardInputFlow = null;" in html
    assert (
        'candidateSource: resolveDashboardCandidateSource(mode, next.candidate_source || ""),'
        in html
    )
    assert "flow_id: dashboardInputFlow.flowId" in html
    assert 'postUiEvent("input_started"' in html
    assert 'await postUiEvent("input_submitted", telemetryData);' in html
    assert 'await postUiEvent("save_success", telemetryData);' in html
    assert "function resolveDashboardCandidateSource(mode, candidateSource) {" in html
    assert 'if (mode === "text") return "free_text";' in html
    assert "payload.candidate_source = flow" in html
    assert 'mode: "tag"' in html
    assert 'mode: "quick"' in html
    assert 'trigger: "candidate_tag"' in html
    assert 'trigger: "dashboard_submit"' in html
    assert "flow.editedBeforeSubmit = true;" in html
    assert "resetDashboardInputFlow();" in html
    assert 'await fetch("/api/candidates")' in html


def test_http_get_dashboard_ignores_broken_pipe_from_client_disconnect(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    handler = _new_handler(handler_cls, "/dashboard")
    handler.wfile = _BrokenPipeWriter()
    handler.do_GET()


def test_http_get_health_ignores_connection_reset_from_client_disconnect(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    handler = _new_handler(handler_cls, "/health")
    handler.wfile = _ConnectionResetWriter()
    handler.do_GET()


def test_http_get_dashboard_fallback_candidates_match_fixed_candidates(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _, _, html = _do_get_html(handler_cls, "/dashboard")
    expected = json.dumps(list(FIXED_CANDIDATES), ensure_ascii=False)
    assert f"var DASHBOARD_FALLBACK_CANDIDATES = {expected};" in html


def test_http_get_dashboard_has_sticky_composer_and_enter_submit(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _, _, html = _do_get_html(handler_cls, "/dashboard")
    assert "#log-form {" in html
    assert "position: sticky;" in html
    assert 'enterkeyhint="done"' in html
    assert 'document.getElementById("log-text").addEventListener("keydown"' in html
    assert 'btn.textContent = "保存中...";' in html


def test_debug_returns_28_entries(data_dir: Path) -> None:
    result = count_events_by_date_debug(28, data_dir=str(data_dir))
    assert len(result) == 28


def test_debug_fields_present(data_dir: Path) -> None:
    result = count_events_by_date_debug(28, data_dir=str(data_dir))
    expected_keys = {"date", "raw_count", "shipped_density", "telemetry_count", "life_count"}
    for item in result:
        assert set(item.keys()) == expected_keys


def test_debug_shipped_density_matches_heatmap(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, domain="mood")
    _add_event(db_path, domain="eng")
    _add_telemetry_event(db_path)
    heatmap = count_events_by_date(28, data_dir=str(data_dir))
    debug = count_events_by_date_debug(28, data_dir=str(data_dir))
    heatmap_by_date = {item["date"]: item["count"] for item in heatmap}
    for item in debug:
        assert item["shipped_density"] == heatmap_by_date[item["date"]]


def test_debug_raw_count_includes_telemetry(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path)
    _add_telemetry_event(db_path)
    result = count_events_by_date_debug(28, data_dir=str(data_dir))
    today_entry = next(item for item in result if item["date"] == _today_local())
    assert today_entry["raw_count"] == 2
    assert today_entry["shipped_density"] == 1
    assert today_entry["telemetry_count"] == 1


def test_debug_telemetry_count_identifies_web_form_ui(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, domain="mood")
    _add_telemetry_event(db_path)
    _add_telemetry_event(db_path)
    result = count_events_by_date_debug(28, data_dir=str(data_dir))
    today_entry = next(item for item in result if item["date"] == _today_local())
    assert today_entry["telemetry_count"] == 2
    assert today_entry["life_count"] == 1


def test_debug_life_count_equals_raw_minus_telemetry(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _add_event(db_path, domain="mood")
    _add_event(db_path, domain="eng")
    _add_telemetry_event(db_path)
    result = count_events_by_date_debug(28, data_dir=str(data_dir))
    today_entry = next(item for item in result if item["date"] == _today_local())
    assert today_entry["life_count"] == today_entry["raw_count"] - today_entry["telemetry_count"]
    assert today_entry["life_count"] == today_entry["shipped_density"]


def test_debug_excludes_summary(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    _append_summary(db_path, _today_utc())
    result = count_events_by_date_debug(28, data_dir=str(data_dir))
    today_entry = next(item for item in result if item["date"] == _today_local())
    assert today_entry["raw_count"] == 0
    assert today_entry["telemetry_count"] == 0


def test_http_get_heatmap_debug_200(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    resp = _do_get_json(handler_cls, "/api/heatmap/debug")
    assert len(resp) == 1
    status, body = resp[0]
    assert status == 200
    assert len(body) == 28
    expected_keys = {"date", "raw_count", "shipped_density", "telemetry_count", "life_count"}
    assert all(set(item.keys()) == expected_keys for item in body)
