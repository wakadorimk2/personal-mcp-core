from pathlib import Path
from personal_mcp.storage.jsonl import append_jsonl, read_jsonl


def test_append_jsonl_two_writes_produce_two_lines(data_dir: Path) -> None:
    path = data_dir / "test.jsonl"
    append_jsonl(path, {"a": 1})
    append_jsonl(path, {"b": 2})

    lines = path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2


def test_append_jsonl_existing_line_is_not_overwritten(data_dir: Path) -> None:
    path = data_dir / "test.jsonl"
    append_jsonl(path, {"key": "original"})
    append_jsonl(path, {"key": "second"})

    records = read_jsonl(path)
    assert records[0] == {"key": "original"}
    assert records[1] == {"key": "second"}
