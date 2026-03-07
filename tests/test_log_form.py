import json
import sqlite3
from pathlib import Path

import pytest

from personal_mcp.tools.log_form import (
    ALLOWED_KINDS,
    DEFAULT_DOMAIN,
    DEFAULT_KIND,
    event_add_sqlite,
    suggest_labels,
)


# ---------------------------------------------------------------------------
# event_add_sqlite
# ---------------------------------------------------------------------------


def test_event_add_sqlite_creates_db_file(data_dir: Path) -> None:
    event_add_sqlite(domain="general", kind="note", data_dir=str(data_dir))
    assert (data_dir / "events.db").exists()


def test_event_add_sqlite_returns_v1_record(data_dir: Path) -> None:
    rec = event_add_sqlite(domain="general", kind="note", text="hello", data_dir=str(data_dir))
    assert rec["v"] == 1
    assert rec["domain"] == "general"
    assert rec["kind"] == "note"
    assert rec["data"]["text"] == "hello"
    assert rec["source"] == "web-form"
    assert "ts" in rec


def test_event_add_sqlite_defaults_domain_kind_when_omitted(data_dir: Path) -> None:
    rec = event_add_sqlite(text="hello", data_dir=str(data_dir))
    assert rec["domain"] == DEFAULT_DOMAIN
    assert rec["kind"] == DEFAULT_KIND


def test_event_add_sqlite_uses_suggested_labels(data_dir: Path) -> None:
    rec = event_add_sqlite(text="PR 実装を完了", data_dir=str(data_dir))
    assert rec["domain"] == "eng"
    assert rec["kind"] == "milestone"


def test_event_add_sqlite_rejects_invalid_domain(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="unsupported domain"):
        event_add_sqlite(domain="unknown", kind="note", data_dir=str(data_dir))


def test_event_add_sqlite_rejects_invalid_kind(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="unsupported kind"):
        event_add_sqlite(domain="general", kind="badkind", data_dir=str(data_dir))


def test_event_add_sqlite_accepts_empty_annotation(data_dir: Path) -> None:
    rec = event_add_sqlite(domain="general", kind="note", annotation="", data_dir=str(data_dir))
    assert "annotation" not in rec.get("data", {})


def test_event_add_sqlite_stores_annotation_in_data(data_dir: Path) -> None:
    rec = event_add_sqlite(domain="general", kind="note", annotation="メモ", data_dir=str(data_dir))
    assert rec["data"]["annotation"] == "メモ"


def test_event_add_sqlite_accepts_empty_text(data_dir: Path) -> None:
    rec = event_add_sqlite(domain="mood", kind="note", text="", data_dir=str(data_dir))
    assert rec["data"]["text"] == ""


@pytest.mark.parametrize("kind", sorted(ALLOWED_KINDS))
def test_event_add_sqlite_accepts_all_allowed_kinds(data_dir: Path, kind: str) -> None:
    rec = event_add_sqlite(domain="general", kind=kind, data_dir=str(data_dir))
    assert rec["kind"] == kind


def test_suggest_labels_defaults_to_general_note() -> None:
    suggested = suggest_labels("just a memo")
    assert suggested == {"domain": DEFAULT_DOMAIN, "kind": DEFAULT_KIND}


# ---------------------------------------------------------------------------
# append_sqlite / DB content
# ---------------------------------------------------------------------------


def test_append_sqlite_raw_is_valid_json(data_dir: Path) -> None:
    event_add_sqlite(domain="eng", kind="artifact", text="test", data_dir=str(data_dir))
    db_path = data_dir / "events.db"
    with sqlite3.connect(str(db_path)) as conn:
        row = conn.execute("SELECT raw FROM events LIMIT 1").fetchone()
    stored = json.loads(row[0])
    assert stored["domain"] == "eng"
    assert stored["kind"] == "artifact"
    assert stored["v"] == 1


def test_append_sqlite_appends_multiple_rows(data_dir: Path) -> None:
    event_add_sqlite(domain="general", kind="note", text="a", data_dir=str(data_dir))
    event_add_sqlite(domain="mood", kind="note", text="b", data_dir=str(data_dir))
    db_path = data_dir / "events.db"
    with sqlite3.connect(str(db_path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 2


def test_db_is_outside_repo(monkeypatch, tmp_path: Path) -> None:
    """DB must not be created inside the repo directory."""
    import personal_mcp

    repo_root = Path(personal_mcp.__file__).parent.parent.parent
    data_dir = tmp_path / "mydata"
    monkeypatch.setenv("PERSONAL_MCP_DATA_DIR", str(data_dir))
    event_add_sqlite(domain="general", kind="note")
    db_path = data_dir / "events.db"
    assert db_path.exists()
    assert not db_path.is_relative_to(repo_root)


# ---------------------------------------------------------------------------
# HTTP handler: routing / validation / response
# ---------------------------------------------------------------------------


def _post_events(handler_cls, body: dict, data_dir: str):
    """Drive do_POST directly without a real socket via io.BytesIO."""
    import io
    from unittest.mock import MagicMock

    raw = json.dumps(body).encode()
    mock_request = MagicMock()
    mock_request.makefile.return_value = io.BytesIO(raw)

    handler = handler_cls.__new__(handler_cls)
    handler.headers = {"Content-Length": str(len(raw)), "Content-Type": "application/json"}
    handler.rfile = io.BytesIO(raw)
    handler.wfile = io.BytesIO()
    handler.path = "/events"
    handler.request_version = "HTTP/1.1"

    responses = []

    def capture_json(status, body_dict):
        responses.append((status, body_dict))

    handler._json = capture_json
    handler.do_POST()
    return responses


def _make_handler_for_test(data_dir: str):
    from personal_mcp.adapters.http_server import _make_handler

    return _make_handler(data_dir)


def test_http_post_events_returns_201_on_valid_input(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(
        handler_cls, {"domain": "general", "kind": "note", "text": "hi"}, str(data_dir)
    )
    assert len(responses) == 1
    status, body = responses[0]
    assert status == 201
    assert body["v"] == 1
    assert body["domain"] == "general"
    assert body["kind"] == "note"


def test_http_post_events_missing_domain_uses_default(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(handler_cls, {"kind": "note", "text": "hi"}, str(data_dir))
    status, body = responses[0]
    assert status == 201
    assert body["domain"] == "general"
    assert body["kind"] == "note"


def test_http_post_events_missing_kind_uses_default(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(handler_cls, {"domain": "general", "text": "hi"}, str(data_dir))
    status, body = responses[0]
    assert status == 201
    assert body["domain"] == "general"
    assert body["kind"] == "note"


def test_http_post_events_missing_both_uses_suggestion(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(handler_cls, {"text": "PR 実装を完了"}, str(data_dir))
    status, body = responses[0]
    assert status == 201
    assert body["domain"] == "eng"
    assert body["kind"] == "milestone"


def test_http_post_events_400_invalid_domain(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(handler_cls, {"domain": "baddom", "kind": "note"}, str(data_dir))
    status, body = responses[0]
    assert status == 400
    assert "domain" in body["error"]


def test_http_post_events_400_invalid_kind(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(handler_cls, {"domain": "general", "kind": "badkind"}, str(data_dir))
    status, body = responses[0]
    assert status == 400
    assert "kind" in body["error"]


def test_http_post_events_400_invalid_content_length(data_dir: Path) -> None:
    import io
    from personal_mcp.adapters.http_server import _make_handler

    handler_cls = _make_handler(str(data_dir))
    handler = handler_cls.__new__(handler_cls)
    handler.headers = {"Content-Length": "notanumber"}
    handler.rfile = io.BytesIO(b"")
    handler.path = "/events"

    responses = []
    handler._json = lambda s, b: responses.append((s, b))
    handler.do_POST()
    assert responses[0][0] == 400
    assert "Content-Length" in responses[0][1]["error"]


def test_http_post_events_saves_to_db(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    _post_events(handler_cls, {"domain": "eng", "kind": "artifact", "text": "saved"}, str(data_dir))
    db_path = data_dir / "events.db"
    assert db_path.exists()
    with sqlite3.connect(str(db_path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 1


def test_http_post_empty_annotation_not_in_data(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_events(
        handler_cls, {"domain": "general", "kind": "note", "annotation": ""}, str(data_dir)
    )
    _, body = responses[0]
    assert "annotation" not in body.get("data", {})


def test_make_html_shows_optional_labels_and_suggestion() -> None:
    from personal_mcp.adapters.http_server import _make_html

    html = _make_html()
    assert 'id="domain" required' not in html
    assert 'id="kind" required' not in html
    assert 'id="suggestion"' in html


# ---------------------------------------------------------------------------
# CLI: web-serve subcommand wiring
# ---------------------------------------------------------------------------


def test_server_main_web_serve_is_registered(monkeypatch) -> None:
    """web-serve subcommand must be reachable and pass parsed args to _cmd_web_serve."""
    import personal_mcp.server as _srv

    calls = []

    def patched(args):
        calls.append((args.host, args.port))
        return 0

    monkeypatch.setattr(_srv, "_cmd_web_serve", patched)
    ret = _srv.main(["web-serve", "--port", "9090"])
    assert ret == 0
    assert calls[0][1] == 9090
