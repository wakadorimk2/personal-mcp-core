import json
from datetime import datetime
from pathlib import Path

import pytest

from personal_mcp.tools.event import event_add, event_list


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _local_date(ts_str: str) -> str:
    """Convert ISO timestamp to local YYYY-MM-DD (timezone-agnostic)."""
    return datetime.fromisoformat(ts_str).astimezone().strftime("%Y-%m-%d")


def _write_events(path: Path, events: list) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# event_add tests (existing)
# ---------------------------------------------------------------------------

def test_event_add_creates_jsonl_with_one_line(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    event_add(domain="poe2", text="test", data_dir=str(data_dir))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["domain"] == "poe2"
    assert record["payload"]["text"] == "test"


def test_event_add_appends_without_overwriting(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text('{"dummy": true}\n', encoding="utf-8")

    event_add(domain="mood", text="second", data_dir=str(data_dir))

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"dummy": True}
    record = json.loads(lines[1])
    assert record["domain"] == "mood"
    assert record["payload"]["text"] == "second"


# ---------------------------------------------------------------------------
# event_list tests
# ---------------------------------------------------------------------------

# Use noon UTC so local date is consistent across UTC-11 to UTC+11 timezones
_TS_DAY1_A = "2026-03-02T12:00:00+00:00"  # day1
_TS_DAY2_A = "2026-03-03T12:00:00+00:00"  # day2 morning
_TS_DAY2_B = "2026-03-03T14:00:00+00:00"  # day2 afternoon

_EVENTS = [
    {"ts": _TS_DAY1_A, "domain": "mood",    "payload": {"text": "day1 mood"},    "tags": []},
    {"ts": _TS_DAY2_A, "domain": "poe2",    "payload": {"text": "day2 poe2"},    "tags": ["farming"]},
    {"ts": _TS_DAY2_B, "domain": "general", "payload": {"text": "day2 general"}, "tags": []},
]


def test_event_list_returns_empty_when_file_missing(data_dir: Path) -> None:
    result = event_list(data_dir=str(data_dir))
    assert result == []


def test_event_list_returns_all_events(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    result = event_list(data_dir=str(data_dir))
    assert len(result) == 3


def test_event_list_newest_first(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    result = event_list(data_dir=str(data_dir))
    texts = [r["payload"]["text"] for r in result]
    # newest event (day2 afternoon) should come first
    assert texts[0] == "day2 general"
    assert texts[-1] == "day1 mood"


def test_event_list_filter_by_domain(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    result = event_list(domain="poe2", data_dir=str(data_dir))
    assert len(result) == 1
    assert result[0]["domain"] == "poe2"
    assert result[0]["payload"]["text"] == "day2 poe2"


def test_event_list_filter_by_date(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    day2 = _local_date(_TS_DAY2_A)
    result = event_list(date=day2, data_dir=str(data_dir))
    assert len(result) == 2
    texts = {r["payload"]["text"] for r in result}
    assert texts == {"day2 poe2", "day2 general"}


def test_event_list_filter_by_date_excludes_other_days(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    day1 = _local_date(_TS_DAY1_A)
    result = event_list(date=day1, data_dir=str(data_dir))
    assert len(result) == 1
    assert result[0]["payload"]["text"] == "day1 mood"


def test_event_list_filter_by_since(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    # since day2 UTC: should exclude day1 event
    result = event_list(since="2026-03-03", data_dir=str(data_dir))
    assert len(result) == 2
    texts = {r["payload"]["text"] for r in result}
    assert "day1 mood" not in texts


def test_event_list_limit_n(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    result = event_list(n=1, data_dir=str(data_dir))
    assert len(result) == 1
    # should be the newest
    assert result[0]["payload"]["text"] == "day2 general"


def test_event_list_empty_for_unmatched_domain(data_dir: Path) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
    result = event_list(domain="nonexistent", data_dir=str(data_dir))
    assert result == []


# ---------------------------------------------------------------------------
# text output format tests (via server.main)
# ---------------------------------------------------------------------------

def test_event_list_text_has_date_header(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)
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


def test_event_list_text_no_output_when_empty(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    from personal_mcp.server import main
    main(["event-list", "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_event_list_json_flag_returns_array(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    _write_events(data_dir / "events.jsonl", _EVENTS)

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
    _write_events(data_dir / "events.jsonl", [_EVENTS[1]])  # day2 poe2 only

    from personal_mcp.server import main
    main(["event-list", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    lines = [l for l in captured.out.splitlines() if not l.startswith("---")]
    assert len(lines) == 1
    # format: HH:MM [domain] text
    import re
    assert re.match(r"^\d{2}:\d{2} \[poe2\] day2 poe2$", lines[0])
