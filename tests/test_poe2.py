import json
from pathlib import Path

import pytest

from personal_mcp.server import main
from personal_mcp.storage.sqlite import append_sqlite, read_sqlite


def _read_runtime_events(data_dir: Path) -> list[dict]:
    return read_sqlite(data_dir / "events.db")


def test_poe2_log_add_writes_to_events_db(data_dir: Path) -> None:
    main(["poe2-log-add", "farming T17 map", "--kind", "session", "--data-dir", str(data_dir)])

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["domain"] == "poe2"
    assert record["data"]["text"] == "farming T17 map"


def test_poe2_log_add_appends_not_overwrites(data_dir: Path) -> None:
    existing = {
        "ts": "2026-03-01T00:00:00+00:00",
        "domain": "general",
        "kind": "note",
        "data": {"text": "first"},
        "tags": [],
        "v": 1,
    }
    append_sqlite(data_dir / "events.db", existing)

    main(["poe2-log-add", "second entry", "--data-dir", str(data_dir)])

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    assert rows[0] == existing
    record = rows[1]
    assert record["domain"] == "poe2"


def test_poe2_log_add_stores_kind_at_top_level(data_dir: Path) -> None:
    main(["poe2-log-add", "note text", "--kind", "note", "--data-dir", str(data_dir)])

    record = _read_runtime_events(data_dir)[0]
    assert record["kind"] == "note"


def test_poe2_log_add_stores_tags(data_dir: Path) -> None:
    main(["poe2-log-add", "tagged entry", "--tags", "mapping,boss", "--data-dir", str(data_dir)])

    record = _read_runtime_events(data_dir)[0]
    assert "mapping" in record["tags"]
    assert "boss" in record["tags"]


def test_poe2_log_list_reads_from_events_db(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    main(
        [
            "poe2-log-add",
            "test entry",
            "--kind",
            "note",
            "--tags",
            "mapping",
            "--data-dir",
            str(data_dir),
        ]
    )
    capsys.readouterr()  # discard poe2-log-add output

    main(["poe2-log-list", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    rows = json.loads(captured.out)
    assert len(rows) == 1
    assert rows[0]["domain"] == "poe2"
    assert rows[0]["data"]["text"] == "test entry"


def test_poe2_log_list_filter_by_kind(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    main(["poe2-log-add", "note entry", "--kind", "note", "--data-dir", str(data_dir)])
    main(["poe2-log-add", "session entry", "--kind", "session", "--data-dir", str(data_dir)])
    capsys.readouterr()  # discard poe2-log-add outputs

    main(["poe2-log-list", "--kind", "note", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    rows = json.loads(captured.out)
    assert len(rows) == 1
    assert rows[0]["data"]["text"] == "note entry"


def test_poe2_log_list_filter_by_tag(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    main(["poe2-log-add", "tagged", "--tags", "boss", "--data-dir", str(data_dir)])
    main(["poe2-log-add", "untagged", "--data-dir", str(data_dir)])
    capsys.readouterr()  # discard poe2-log-add outputs

    main(["poe2-log-list", "--tag", "boss", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    rows = json.loads(captured.out)
    assert len(rows) == 1
    assert rows[0]["data"]["text"] == "tagged"
