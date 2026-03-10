import json
import sqlite3
from pathlib import Path

import pytest

from personal_mcp.tools.log_form import (
    ALLOWED_KINDS,
    ALLOWED_UI_EVENT_NAMES,
    ALLOWED_UI_MODES,
    DEFAULT_DOMAIN,
    DEFAULT_KIND,
    event_add_sqlite,
    suggest_labels,
    ui_event_add_sqlite,
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


def test_ui_event_add_sqlite_returns_v1_record(data_dir: Path) -> None:
    rec = ui_event_add_sqlite(event_name="ui_mode_changed", ui_mode="quick", data_dir=str(data_dir))
    assert rec["v"] == 1
    assert rec["domain"] == "general"
    assert rec["kind"] == "interaction"
    assert rec["source"] == "web-form-ui"
    assert rec["data"]["event_name"] == "ui_mode_changed"
    assert rec["data"]["ui_mode"] == "quick"


@pytest.mark.parametrize("event_name", sorted(ALLOWED_UI_EVENT_NAMES))
def test_ui_event_add_sqlite_accepts_all_ui_event_names(data_dir: Path, event_name: str) -> None:
    rec = ui_event_add_sqlite(event_name=event_name, ui_mode="tag", data_dir=str(data_dir))
    assert rec["data"]["event_name"] == event_name


@pytest.mark.parametrize("ui_mode", sorted(ALLOWED_UI_MODES))
def test_ui_event_add_sqlite_accepts_all_ui_modes(data_dir: Path, ui_mode: str) -> None:
    rec = ui_event_add_sqlite(event_name="input_started", ui_mode=ui_mode, data_dir=str(data_dir))
    assert rec["data"]["ui_mode"] == ui_mode


def test_ui_event_add_sqlite_rejects_invalid_event_name(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="unsupported ui event"):
        ui_event_add_sqlite(event_name="invalid_event", ui_mode="quick", data_dir=str(data_dir))


def test_ui_event_add_sqlite_rejects_invalid_ui_mode(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="unsupported ui mode"):
        ui_event_add_sqlite(
            event_name="input_submitted", ui_mode="keyboard", data_dir=str(data_dir)
        )


def test_ui_event_add_sqlite_input_submitted_enriches_min_contract(data_dir: Path) -> None:
    rec = ui_event_add_sqlite(
        event_name="input_submitted",
        ui_mode="quick",
        data_dir=str(data_dir),
        extra_data={"edited_before_submit": "true", "trigger": "quick_chip"},
    )
    assert rec["data"]["mode"] == "quick"
    assert rec["data"]["save_type"] == "instant"
    assert rec["data"]["edited_before_submit"] is True
    assert rec["data"]["trigger"] == "quick_chip"


@pytest.mark.parametrize(
    ("ui_mode", "expected_save_type", "expected_trigger"),
    [
        ("quick", "instant", "quick_chip"),
        ("tag", "manual", "candidate_tag"),
        ("text", "manual", "text_submit"),
    ],
)
def test_ui_event_add_sqlite_input_submitted_applies_mode_defaults(
    data_dir: Path,
    ui_mode: str,
    expected_save_type: str,
    expected_trigger: str,
) -> None:
    rec = ui_event_add_sqlite(
        event_name="input_submitted",
        ui_mode=ui_mode,
        data_dir=str(data_dir),
        extra_data={},
    )
    assert rec["data"]["mode"] == ui_mode
    assert rec["data"]["save_type"] == expected_save_type
    assert rec["data"]["edited_before_submit"] is False
    assert rec["data"]["trigger"] == expected_trigger


def test_ui_event_add_sqlite_input_submitted_dashboard_uses_explicit_mode(data_dir: Path) -> None:
    rec = ui_event_add_sqlite(
        event_name="input_submitted",
        ui_mode="dashboard",
        data_dir=str(data_dir),
        extra_data={
            "mode": "quick",
            "trigger": "candidate_quick_save",
            "candidate_source": "recent",
            "flow_id": "dashboard-123",
        },
    )
    assert rec["data"]["ui_mode"] == "dashboard"
    assert rec["data"]["mode"] == "quick"
    assert rec["data"]["save_type"] == "instant"
    assert rec["data"]["edited_before_submit"] is False
    assert rec["data"]["trigger"] == "candidate_quick_save"
    assert rec["data"]["candidate_source"] == "recent"
    assert rec["data"]["flow_id"] == "dashboard-123"


def test_ui_event_add_sqlite_input_submitted_dashboard_rejects_missing_mode(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="unsupported input mode"):
        ui_event_add_sqlite(
            event_name="input_submitted",
            ui_mode="dashboard",
            data_dir=str(data_dir),
            extra_data={},
        )


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


def _post_json(handler_cls, body: dict, path: str):
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
    handler.path = path
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
    responses = _post_json(
        handler_cls, {"domain": "general", "kind": "note", "text": "hi"}, "/events"
    )
    assert len(responses) == 1
    status, body = responses[0]
    assert status == 201
    assert body["v"] == 1
    assert body["domain"] == "general"
    assert body["kind"] == "note"


def test_http_post_events_missing_domain_uses_default(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(handler_cls, {"kind": "note", "text": "hi"}, "/events")
    status, body = responses[0]
    assert status == 201
    assert body["domain"] == "general"
    assert body["kind"] == "note"


def test_http_post_events_missing_kind_uses_default(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(handler_cls, {"domain": "general", "text": "hi"}, "/events")
    status, body = responses[0]
    assert status == 201
    assert body["domain"] == "general"
    assert body["kind"] == "note"


def test_http_post_events_missing_both_uses_suggestion(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(handler_cls, {"text": "PR 実装を完了"}, "/events")
    status, body = responses[0]
    assert status == 201
    assert body["domain"] == "eng"
    assert body["kind"] == "milestone"


def test_http_post_events_400_invalid_domain(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(handler_cls, {"domain": "baddom", "kind": "note"}, "/events")
    status, body = responses[0]
    assert status == 400
    assert "domain" in body["error"]


def test_http_post_events_400_invalid_kind(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(handler_cls, {"domain": "general", "kind": "badkind"}, "/events")
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
    _post_json(handler_cls, {"domain": "eng", "kind": "artifact", "text": "saved"}, "/events")
    db_path = data_dir / "events.db"
    assert db_path.exists()
    with sqlite3.connect(str(db_path)) as conn:
        count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    assert count == 1


def test_http_post_empty_annotation_not_in_data(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls, {"domain": "general", "kind": "note", "annotation": ""}, "/events"
    )
    _, body = responses[0]
    assert "annotation" not in body.get("data", {})


def test_http_post_ui_events_returns_201_on_valid_input(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls,
        {
            "event_name": "ui_mode_changed",
            "ui_mode": "quick",
            "extra_data": {"from_mode": "text", "to_mode": "quick"},
        },
        "/events/ui",
    )
    assert len(responses) == 1
    status, body = responses[0]
    assert status == 201
    assert body["kind"] == "interaction"
    assert body["data"]["event_name"] == "ui_mode_changed"
    assert body["data"]["ui_mode"] == "quick"
    assert body["data"]["from_mode"] == "text"


def test_http_post_ui_events_returns_201_on_dashboard_refresh_event(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls,
        {
            "event_name": "refresh_triggered",
            "ui_mode": "dashboard",
            "extra_data": {"source": "manual"},
        },
        "/events/ui",
    )
    status, body = responses[0]
    assert status == 201
    assert body["data"]["event_name"] == "refresh_triggered"
    assert body["data"]["ui_mode"] == "dashboard"
    assert body["data"]["source"] == "manual"


def test_http_post_ui_events_400_invalid_ui_mode(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls,
        {"event_name": "input_started", "ui_mode": "keyboard"},
        "/events/ui",
    )
    status, body = responses[0]
    assert status == 400
    assert "ui mode" in body["error"]


def test_http_post_ui_events_400_non_object_extra_data(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls,
        {"event_name": "input_started", "ui_mode": "tag", "extra_data": "bad"},
        "/events/ui",
    )
    status, body = responses[0]
    assert status == 400
    assert "extra_data" in body["error"]


def test_http_post_ui_events_input_submitted_fills_contract_defaults(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls,
        {
            "event_name": "input_submitted",
            "ui_mode": "tag",
            "extra_data": {"edited_before_submit": "1"},
        },
        "/events/ui",
    )
    status, body = responses[0]
    assert status == 201
    assert body["data"]["mode"] == "tag"
    assert body["data"]["save_type"] == "manual"
    assert body["data"]["edited_before_submit"] is True
    assert body["data"]["trigger"] == "candidate_tag"


def test_http_post_ui_events_dashboard_accepts_explicit_input_mode(data_dir: Path) -> None:
    handler_cls = _make_handler_for_test(str(data_dir))
    responses = _post_json(
        handler_cls,
        {
            "event_name": "input_submitted",
            "ui_mode": "dashboard",
            "extra_data": {
                "mode": "tag",
                "trigger": "candidate_tag",
                "candidate_source": "recent",
                "edited_before_submit": True,
            },
        },
        "/events/ui",
    )
    status, body = responses[0]
    assert status == 201
    assert body["data"]["ui_mode"] == "dashboard"
    assert body["data"]["mode"] == "tag"
    assert body["data"]["save_type"] == "manual"
    assert body["data"]["trigger"] == "candidate_tag"
    assert body["data"]["candidate_source"] == "recent"
    assert body["data"]["edited_before_submit"] is True


def test_make_html_shows_optional_labels_and_suggestion() -> None:
    from personal_mcp.adapters.http_server import _make_html

    html = _make_html()
    assert 'id="domain" required' not in html
    assert 'id="kind" required' not in html
    assert 'id="suggestion"' in html
    assert 'data-mode="quick"' in html
    assert 'data-mode="tag"' in html
    assert 'data-mode="text"' in html


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
