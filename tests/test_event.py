import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from personal_mcp.core.event import build_v1_record
from personal_mcp.core.event import ALLOWED_DOMAINS
from personal_mcp.storage.events_store import rebuild_db_from_jsonl
from personal_mcp.storage.sqlite import append_sqlite, read_sqlite
from personal_mcp.tools.event import event_add, event_list


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _local_date(ts_str: str) -> str:
    """Convert ISO timestamp to local YYYY-MM-DD (timezone-agnostic)."""
    return datetime.fromisoformat(ts_str).astimezone().strftime("%Y-%m-%d")


def _write_events(path: Path, events: list) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


def _seed_runtime_events(data_dir: Path, events: list[dict]) -> None:
    db_path = data_dir / "events.db"
    for event in events:
        append_sqlite(db_path, event)


def _read_runtime_events(data_dir: Path) -> list[dict]:
    return read_sqlite(data_dir / "events.db")


# ---------------------------------------------------------------------------
# event_add tests (existing)
# ---------------------------------------------------------------------------


def test_event_add_creates_db_with_one_row(data_dir: Path) -> None:
    event_add(domain="poe2", text="test", data_dir=str(data_dir))

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["domain"] == "poe2"
    assert record["data"]["text"] == "test"


def test_event_add_uses_env_data_dir_when_omitted(monkeypatch, tmp_path: Path) -> None:
    data_dir = tmp_path / "env_data"
    monkeypatch.setenv("PERSONAL_MCP_DATA_DIR", str(data_dir))

    event_add(domain="poe2", text="test")

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["data"]["text"] == "test"


def test_event_add_appends_without_overwriting(data_dir: Path) -> None:
    existing = build_v1_record(
        ts="2026-03-01T00:00:00+00:00",
        domain="general",
        text="first",
        tags=[],
        kind="note",
    )
    append_sqlite(data_dir / "events.db", existing)

    event_add(domain="mood", text="second", data_dir=str(data_dir))

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    assert rows[0] == existing
    record = rows[1]
    assert record["domain"] == "mood"
    assert record["data"]["text"] == "second"


@pytest.mark.parametrize("domain", ["eng", "worklog", "summary"])
def test_event_add_accepts_new_allowed_domains(data_dir: Path, domain: str) -> None:
    event_add(domain=domain, text=f"{domain} entry", data_dir=str(data_dir))

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["domain"] == domain
    assert record["data"]["text"] == f"{domain} entry"


def test_event_add_rejects_disallowed_domain_without_writing(data_dir: Path) -> None:
    with pytest.raises(ValueError, match="unsupported domain: art"):
        event_add(domain="art", text="bad domain", data_dir=str(data_dir))

    assert not (data_dir / "events.db").exists()
    assert not (data_dir / "events.jsonl").exists()


def test_event_add_writes_v1_field(data_dir: Path) -> None:
    record = event_add(domain="general", text="versioned", data_dir=str(data_dir))
    assert record["v"] == 1


def test_event_add_writes_v1_shape_without_payload(data_dir: Path) -> None:
    record = event_add(domain="general", text="shape", data_dir=str(data_dir))
    assert "payload" not in record
    assert record["data"]["text"] == "shape"


def test_event_add_promotes_source_ref_and_keeps_other_meta_in_data(data_dir: Path) -> None:
    record = event_add(
        domain="poe2",
        text="entered hideout",
        kind="area_transition",
        meta={
            "source": "client_txt",
            "ref": "line:1",
            "raw": "[SCENE] Set Source [Hideout]",
        },
        data_dir=str(data_dir),
    )
    assert record["kind"] == "area_transition"
    assert record["source"] == "client_txt"
    assert record["ref"] == "line:1"
    assert record["data"]["raw"] == "[SCENE] Set Source [Hideout]"


def test_event_add_does_not_promote_meta_kind_without_kind_arg(data_dir: Path) -> None:
    record = event_add(
        domain="poe2",
        text="meta kind",
        meta={"kind": "from-meta"},
        data_dir=str(data_dir),
    )
    assert "kind" not in record
    assert record["data"]["kind"] == "from-meta"


def test_allowed_domains_keeps_existing_supported_domains() -> None:
    assert {"poe2", "mood", "general", "summary"}.issubset(ALLOWED_DOMAINS)


# ---------------------------------------------------------------------------
# event_list tests
# ---------------------------------------------------------------------------

# writer output/event-list tests should use v1 fixtures.
# legacy shape fixtures are allowed only in explicit compatibility tests.
_TS_DAY1_A = "2026-03-02T12:00:00+00:00"  # day1
_TS_DAY2_A = "2026-03-03T12:00:00+00:00"  # day2 morning
_TS_DAY2_B = "2026-03-03T14:00:00+00:00"  # day2 afternoon

_EVENTS = [
    {
        "ts": _TS_DAY1_A,
        "domain": "mood",
        "kind": "note",
        "data": {"text": "day1 mood"},
        "tags": [],
        "v": 1,
    },
    {
        "ts": _TS_DAY2_A,
        "domain": "poe2",
        "kind": "session",
        "data": {"text": "day2 poe2"},
        "tags": ["farming"],
        "v": 1,
    },
    {
        "ts": _TS_DAY2_B,
        "domain": "general",
        "kind": "note",
        "data": {"text": "day2 general"},
        "tags": [],
        "v": 1,
    },
]


def test_event_list_returns_empty_when_file_missing(data_dir: Path) -> None:
    result = event_list(data_dir=str(data_dir))
    assert result == []


def test_event_list_returns_all_events(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    result = event_list(data_dir=str(data_dir))
    assert len(result) == 3


def test_event_list_newest_first(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    result = event_list(data_dir=str(data_dir))
    texts = [r["data"]["text"] for r in result]
    # newest event (day2 afternoon) should come first
    assert texts[0] == "day2 general"
    assert texts[-1] == "day1 mood"


def test_event_list_filter_by_domain(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    result = event_list(domain="poe2", data_dir=str(data_dir))
    assert len(result) == 1
    assert result[0]["domain"] == "poe2"
    assert result[0]["data"]["text"] == "day2 poe2"


def test_event_list_filter_by_date(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    day2 = _local_date(_TS_DAY2_A)
    result = event_list(date=day2, data_dir=str(data_dir))
    assert len(result) == 2
    texts = {r["data"]["text"] for r in result}
    assert texts == {"day2 poe2", "day2 general"}


def test_event_list_filter_by_date_excludes_other_days(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    day1 = _local_date(_TS_DAY1_A)
    result = event_list(date=day1, data_dir=str(data_dir))
    assert len(result) == 1
    assert result[0]["data"]["text"] == "day1 mood"


def test_event_list_tolerates_legacy_records_missing_v(data_dir: Path) -> None:
    # Legacy JSONL is normalized only through the recovery migration path.
    legacy_event = {
        "ts": _TS_DAY2_A,
        "domain": "general",
        "payload": {"text": "legacy"},
        "tags": [],
    }
    _write_events(data_dir / "events.jsonl", [legacy_event])
    rebuild_db_from_jsonl(data_dir=str(data_dir))

    result = event_list(data_dir=str(data_dir))

    assert len(result) == 1
    assert result[0]["data"]["text"] == "legacy"
    assert "v" not in result[0]


def test_event_list_includes_legacy_records_missing_kind(data_dir: Path) -> None:
    # Legacy JSONL is normalized only through the recovery migration path.
    legacy_event = {
        "ts": _TS_DAY2_A,
        "domain": "poe2",
        "payload": {"text": "no-kind"},
        "tags": [],
    }
    _write_events(data_dir / "events.jsonl", [legacy_event])
    rebuild_db_from_jsonl(data_dir=str(data_dir))

    result = event_list(data_dir=str(data_dir))

    assert len(result) == 1
    assert result[0]["data"]["text"] == "no-kind"
    assert "kind" not in result[0]


def test_event_list_filter_by_since(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    # since day2 UTC: should exclude day1 event
    result = event_list(since="2026-03-03", data_dir=str(data_dir))
    assert len(result) == 2
    texts = {r["data"]["text"] for r in result}
    assert "day1 mood" not in texts


def test_event_list_limit_n(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    result = event_list(n=1, data_dir=str(data_dir))
    assert len(result) == 1
    # should be the newest
    assert result[0]["data"]["text"] == "day2 general"


def test_event_list_empty_for_unmatched_domain(data_dir: Path) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    result = event_list(domain="nonexistent", data_dir=str(data_dir))
    assert result == []


# ---------------------------------------------------------------------------
# mood-add tests (via server.main)
# ---------------------------------------------------------------------------


def test_mood_add_writes_mood_domain(data_dir: Path) -> None:
    from personal_mcp.server import main

    main(["mood-add", "少し疲れた", "--data-dir", str(data_dir)])

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["domain"] == "mood"
    assert record["data"]["text"] == "少し疲れた"


def test_mood_add_no_numeric_score_in_data(data_dir: Path) -> None:
    from personal_mcp.server import main

    main(["mood-add", "まあまあ", "--data-dir", str(data_dir)])

    record = _read_runtime_events(data_dir)[0]
    data = record.get("data", {})
    numeric_keys = [k for k, v in data.items() if isinstance(v, (int, float))]
    assert numeric_keys == [], f"numeric keys found in data: {numeric_keys}"


def test_mood_add_with_tags(data_dir: Path) -> None:
    from personal_mcp.server import main

    main(["mood-add", "元気", "--tags", "work,tired", "--data-dir", str(data_dir)])

    record = _read_runtime_events(data_dir)[0]
    assert record["domain"] == "mood"
    assert "work" in record["tags"]
    assert "tired" in record["tags"]


def test_mood_add_appends_to_existing_events(data_dir: Path) -> None:
    existing = build_v1_record(
        ts="2026-03-01T00:00:00+00:00",
        domain="general",
        text="first",
        tags=[],
        kind="note",
    )
    append_sqlite(data_dir / "events.db", existing)

    from personal_mcp.server import main

    main(["mood-add", "追記テスト", "--data-dir", str(data_dir)])

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    assert rows[0] == existing
    record = rows[1]
    assert record["domain"] == "mood"


# ---------------------------------------------------------------------------
# text output format tests (via server.main)
# ---------------------------------------------------------------------------


def test_event_list_text_has_date_header(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _seed_runtime_events(data_dir, _EVENTS)
    day2 = _local_date(_TS_DAY2_A)

    from personal_mcp.server import main

    main(["event-list", "--date", day2, "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert f"--- {day2} ---" in captured.out
    assert "[poe2]" in captured.out
    assert "[general]" in captured.out
    # must not contain other date's header
    day1 = _local_date(_TS_DAY1_A)
    if day1 != day2:
        assert f"--- {day1} ---" not in captured.out


def test_event_list_text_no_output_when_empty(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    from personal_mcp.server import main

    main(["event-list", "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_event_list_json_flag_returns_array(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _seed_runtime_events(data_dir, _EVENTS)

    from personal_mcp.server import main

    main(["event-list", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert len(parsed) == 3
    # no text headers in JSON output
    assert "---" not in captured.out


def test_event_list_json_empty_is_array(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    from personal_mcp.server import main

    main(["event-list", "--json", "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == []


def test_event_list_text_line_format(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    """Each detail line must match 'HH:MM [domain] text'."""
    _seed_runtime_events(data_dir, [_EVENTS[1]])  # day2 poe2 only

    from personal_mcp.server import main

    main(["event-list", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if not l.startswith("---")]  # noqa: E741
    assert len(lines) == 1
    # format: HH:MM [domain] text
    assert re.match(r"^\d{2}:\d{2} \[poe2\] day2 poe2$", lines[0])


# ---------------------------------------------------------------------------
# event-today tests (via server.main)
# ---------------------------------------------------------------------------


# Build test timestamps from local noon so event-today stays stable near UTC date boundaries.
def _today_local_noon() -> str:
    return (
        datetime.now().astimezone().replace(hour=12, minute=0, second=0, microsecond=0).isoformat()
    )


def _yesterday_local_noon() -> str:
    return (
        (datetime.now().astimezone() - timedelta(days=1))
        .replace(hour=12, minute=0, second=0, microsecond=0)
        .isoformat()
    )


def test_event_today_returns_only_today(data_dir: Path) -> None:
    events = [
        {
            "ts": _yesterday_local_noon(),
            "domain": "mood",
            "kind": "note",
            "data": {"text": "yesterday"},
            "tags": [],
            "v": 1,
        },
        {
            "ts": _today_local_noon(),
            "domain": "poe2",
            "kind": "session",
            "data": {"text": "today"},
            "tags": [],
            "v": 1,
        },
    ]
    _seed_runtime_events(data_dir, events)

    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    from personal_mcp.tools.event import event_list as _event_list

    result = _event_list(date=today, data_dir=str(data_dir))
    assert len(result) == 1
    assert result[0]["data"]["text"] == "today"


def test_event_today_excludes_yesterday(data_dir: Path) -> None:
    events = [
        {
            "ts": _yesterday_local_noon(),
            "domain": "mood",
            "kind": "note",
            "data": {"text": "old"},
            "tags": [],
            "v": 1,
        },
    ]
    _seed_runtime_events(data_dir, events)

    today = datetime.now().astimezone().strftime("%Y-%m-%d")
    from personal_mcp.tools.event import event_list as _event_list

    result = _event_list(date=today, data_dir=str(data_dir))
    assert result == []


def test_event_today_text_no_date_header(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    """event-today must not print '--- YYYY-MM-DD ---' headers."""
    events = [
        {
            "ts": _today_local_noon(),
            "domain": "mood",
            "kind": "note",
            "data": {"text": "hello"},
            "tags": [],
            "v": 1,
        },
    ]
    _seed_runtime_events(data_dir, events)

    from personal_mcp.server import main

    main(["event-today", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert "---" not in captured.out
    assert "[mood] hello" in captured.out


def test_event_today_text_handles_legacy_record_missing_kind(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    # Legacy JSONL is normalized only through the recovery migration path.
    events = [
        {
            "ts": _today_local_noon(),
            "domain": "poe2",
            "payload": {"text": "legacy today"},
            "tags": [],
        },
    ]
    _write_events(data_dir / "events.jsonl", events)
    rebuild_db_from_jsonl(data_dir=str(data_dir))

    from personal_mcp.server import main

    main(["event-today", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert "[poe2] legacy today" in captured.out
    assert "[?]" not in captured.out


def test_event_today_text_line_format(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    """Each line must match 'HH:MM [domain] text' exactly."""
    events = [
        {
            "ts": _today_local_noon(),
            "domain": "general",
            "kind": "note",
            "data": {"text": "line check"},
            "tags": [],
            "v": 1,
        },
    ]
    _seed_runtime_events(data_dir, events)

    from personal_mcp.server import main

    main(["event-today", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    lines = captured.out.strip().splitlines()
    assert len(lines) == 1
    assert re.match(r"^\d{2}:\d{2} \[general\] line check$", lines[0])


def test_event_today_empty_output_when_no_events(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    """No events today → empty output (no messages, no headers)."""
    from personal_mcp.server import main

    main(["event-today", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_event_today_domain_filter(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    events = [
        {
            "ts": _today_local_noon(),
            "domain": "mood",
            "kind": "note",
            "data": {"text": "mood event"},
            "tags": [],
            "v": 1,
        },
        {
            "ts": _today_local_noon(),
            "domain": "poe2",
            "kind": "session",
            "data": {"text": "poe2 event"},
            "tags": [],
            "v": 1,
        },
    ]
    _seed_runtime_events(data_dir, events)

    from personal_mcp.server import main

    main(["event-today", "--domain", "mood", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert "[mood] mood event" in captured.out
    assert "poe2" not in captured.out


def test_event_today_json_flag(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    events = [
        {
            "ts": _today_local_noon(),
            "domain": "mood",
            "kind": "note",
            "data": {"text": "json check"},
            "tags": [],
            "v": 1,
        },
    ]
    _seed_runtime_events(data_dir, events)

    from personal_mcp.server import main

    main(["event-today", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert isinstance(parsed, list)
    assert len(parsed) == 1
    assert parsed[0]["domain"] == "mood"
    assert "---" not in captured.out


def test_event_today_json_empty_is_array(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    from personal_mcp.server import main

    main(["event-today", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    parsed = json.loads(captured.out)
    assert parsed == []
