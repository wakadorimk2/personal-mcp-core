import json
from pathlib import Path

import pytest

from personal_mcp.server import main


def test_poe2_log_add_writes_to_events_jsonl(data_dir: Path) -> None:
    main(["poe2-log-add", "farming T17 map", "--kind", "session", "--data-dir", str(data_dir)])

    path = data_dir / "events.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["domain"] == "poe2"
    assert record["payload"]["text"] == "farming T17 map"


def test_poe2_log_add_appends_not_overwrites(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text('{"dummy": true}\n', encoding="utf-8")

    main(["poe2-log-add", "second entry", "--data-dir", str(data_dir)])

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"dummy": True}
    record = json.loads(lines[1])
    assert record["domain"] == "poe2"


def test_poe2_log_add_stores_kind_in_payload(data_dir: Path) -> None:
    main(["poe2-log-add", "note text", "--kind", "note", "--data-dir", str(data_dir)])

    path = data_dir / "events.jsonl"
    record = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert record["payload"]["meta"]["kind"] == "note"


def test_poe2_log_add_stores_tags(data_dir: Path) -> None:
    main(["poe2-log-add", "tagged entry", "--tags", "mapping,boss", "--data-dir", str(data_dir)])

    path = data_dir / "events.jsonl"
    record = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert "mapping" in record["tags"]
    assert "boss" in record["tags"]


def test_poe2_log_list_reads_from_events_jsonl(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
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
    assert rows[0]["payload"]["text"] == "test entry"


def test_poe2_log_list_filter_by_kind(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    main(["poe2-log-add", "note entry", "--kind", "note", "--data-dir", str(data_dir)])
    main(["poe2-log-add", "session entry", "--kind", "session", "--data-dir", str(data_dir)])
    capsys.readouterr()  # discard poe2-log-add outputs

    main(["poe2-log-list", "--kind", "note", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    rows = json.loads(captured.out)
    assert len(rows) == 1
    assert rows[0]["payload"]["text"] == "note entry"


def test_poe2_log_list_filter_by_tag(data_dir: Path, capsys: pytest.CaptureFixture) -> None:
    main(["poe2-log-add", "tagged", "--tags", "boss", "--data-dir", str(data_dir)])
    main(["poe2-log-add", "untagged", "--data-dir", str(data_dir)])
    capsys.readouterr()  # discard poe2-log-add outputs

    main(["poe2-log-list", "--tag", "boss", "--json", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    rows = json.loads(captured.out)
    assert len(rows) == 1
    assert rows[0]["payload"]["text"] == "tagged"
