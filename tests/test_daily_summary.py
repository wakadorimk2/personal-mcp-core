from __future__ import annotations

import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.sqlite import append_sqlite
from personal_mcp.tools.daily_summary import generate_daily_summary, get_latest_summary
from personal_mcp.tools.log_form import event_add_sqlite

_DATE = "2026-03-07"


def test_generate_creates_v1_summary_record(data_dir: Path) -> None:
    record = generate_daily_summary(_DATE, data_dir=str(data_dir))
    assert record["v"] == 1
    assert record["domain"] == "summary"
    assert record["kind"] == "artifact"
    assert record["source"] == "generated"
    assert record["data"]["date"] == _DATE
    assert "ts" in record


def test_generate_appends_to_sqlite(data_dir: Path) -> None:
    generate_daily_summary(_DATE, data_dir=str(data_dir))
    db_path = data_dir / "events.db"
    with sqlite3.connect(str(db_path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 1


def test_generate_empty_events_returns_placeholder(data_dir: Path) -> None:
    record = generate_daily_summary(_DATE, data_dir=str(data_dir))
    assert record["data"]["text"] == "(記録なし)"


def test_generate_reads_web_form_events_from_sqlite(data_dir: Path) -> None:
    event_add_sqlite(domain="mood", kind="note", text="元気", data_dir=str(data_dir))
    record = generate_daily_summary(
        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        data_dir=str(data_dir),
    )
    assert "mood" in record["data"]["text"]
    assert "元気" in record["data"]["text"]


def test_generate_uses_utc_date_normalization(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    record = build_v1_record(
        ts="2026-03-07T00:30:00+09:00",
        domain="eng",
        text="tz boundary",
        tags=[],
        kind="note",
        source="manual",
    )
    append_sqlite(db_path, record)

    utc_match = generate_daily_summary("2026-03-06", data_dir=str(data_dir))
    utc_miss = generate_daily_summary("2026-03-07", data_dir=str(data_dir))
    assert "eng" in utc_match["data"]["text"]
    assert utc_miss["data"]["text"] == "(記録なし)"


def test_generate_excludes_existing_summary_events(data_dir: Path) -> None:
    summary_record = build_v1_record(
        ts="2026-03-07T12:00:00+00:00",
        domain="summary",
        text="old",
        tags=[],
        kind="artifact",
        source="generated",
        extra_data={"date": _DATE},
    )
    append_sqlite(data_dir / "events.db", summary_record)
    record = generate_daily_summary(_DATE, data_dir=str(data_dir))
    assert record["data"]["text"] == "(記録なし)"


def test_generate_with_annotation_and_interpretation(data_dir: Path) -> None:
    record = generate_daily_summary(
        _DATE,
        annotation="注釈",
        interpretation="解釈",
        data_dir=str(data_dir),
    )
    assert record["data"]["annotation"] == "注釈"
    assert record["data"]["interpretation"] == "解釈"


def test_generate_rerun_appends_and_latest_wins(data_dir: Path) -> None:
    generate_daily_summary(_DATE, annotation="first", data_dir=str(data_dir))
    generate_daily_summary(_DATE, annotation="second", data_dir=str(data_dir))
    latest = get_latest_summary(_DATE, data_dir=str(data_dir))
    assert latest is not None
    assert latest["data"]["annotation"] == "second"


def test_get_latest_summary_returns_none_when_no_db(data_dir: Path) -> None:
    assert get_latest_summary(_DATE, data_dir=str(data_dir)) is None


def test_get_latest_summary_returns_none_for_different_date(data_dir: Path) -> None:
    generate_daily_summary("2026-03-06", data_dir=str(data_dir))
    assert get_latest_summary(_DATE, data_dir=str(data_dir)) is None


def test_cli_summary_generate_json_flag(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    from personal_mcp.server import main

    main(["summary-generate", "--date", _DATE, "--json", "--data-dir", str(data_dir)])
    record = json.loads(capsys.readouterr().out)
    assert record["domain"] == "summary"
    assert record["data"]["date"] == _DATE


def test_cli_summary_generate_default_date_is_utc(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    from personal_mcp.server import main

    main(["summary-generate", "--json", "--data-dir", str(data_dir)])
    record = json.loads(capsys.readouterr().out)
    ts_utc_date = datetime.fromisoformat(record["ts"]).astimezone(timezone.utc).strftime("%Y-%m-%d")
    assert record["data"]["date"] == ts_utc_date


def test_cli_summary_generate_text_output_contains_date(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    from personal_mcp.server import main

    main(["summary-generate", "--date", _DATE, "--data-dir", str(data_dir)])
    assert _DATE in capsys.readouterr().out


def test_cli_heatmap_density_audit_json_uses_365_day_primary_window(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    from personal_mcp.server import main

    event_add_sqlite(domain="mood", kind="note", text="x", data_dir=str(data_dir))

    main(["heatmap-density-audit", "--json", "--data-dir", str(data_dir)])
    result = json.loads(capsys.readouterr().out)

    assert result["policy"]["primary_window_days"] == 365
    assert result["primary_window"]["label"] == "last_365_days"
    assert result["primary_window"]["heuristic_flags"]["advisory_only"] is True


def _get_summaries(handler_cls, path: str):
    handler = handler_cls.__new__(handler_cls)
    handler.headers = {}
    handler.rfile = io.BytesIO(b"")
    handler.wfile = io.BytesIO()
    handler.path = path
    handler.request_version = "HTTP/1.1"

    responses = []
    handler._json = lambda s, b: responses.append((s, b))
    handler.do_GET()
    return responses


def _make_handler_for_test(data_dir: str):
    from personal_mcp.adapters.http_server import _make_handler

    return _make_handler(data_dir)


def test_http_get_summaries_404_when_missing(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    status, _ = _get_summaries(handler_cls, f"/summaries?date={_DATE}")[0]
    assert status == 404


def test_http_get_summaries_200_with_record(data_dir: Path) -> None:
    generate_daily_summary(_DATE, data_dir=str(data_dir))
    handler_cls = _make_handler_for_test(str(data_dir))
    status, body = _get_summaries(handler_cls, f"/summaries?date={_DATE}")[0]
    assert status == 200
    assert body["domain"] == "summary"
    assert body["data"]["date"] == _DATE


def test_http_get_summaries_400_without_date(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    status, body = _get_summaries(handler_cls, "/summaries")[0]
    assert status == 400
    assert "date" in body["error"]
