import json
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


def test_read_jsonl_normalizes_legacy_record_without_adding_v(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "ts": "2026-03-04T09:00:00+00:00",
                "domain": "poe2",
                "payload": {
                    "text": "entered hideout",
                    "area": "Hideout",
                    "meta": {
                        "kind": "area_transition",
                        "source": "client_txt",
                        "raw": "[SCENE] Set Source [Hideout]",
                    },
                },
                "tags": ["auto"],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_jsonl(path)

    assert records == [
        {
            "ts": "2026-03-04T09:00:00+00:00",
            "domain": "poe2",
            "kind": "area_transition",
            "source": "client_txt",
            "data": {
                "text": "entered hideout",
                "area": "Hideout",
                "raw": "[SCENE] Set Source [Hideout]",
            },
            "tags": ["auto"],
        }
    ]


def test_read_jsonl_preserves_payload_sibling_keys_during_normalization(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "ts": "2026-03-04T09:00:00+00:00",
                "domain": "general",
                "payload": {
                    "text": "legacy payload",
                    "topic": "schema",
                    "meta": {"kind": "note", "topic": "ignored-meta-duplicate"},
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_jsonl(path)

    assert records[0]["data"] == {"text": "legacy payload", "topic": "schema"}
    assert "payload" not in records[0]
    assert "v" not in records[0]


def test_read_jsonl_passes_through_v1_data_record(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "ts": "2026-03-04T10:00:00Z",
                "domain": "general",
                "kind": "note",
                "data": {"text": "v1 text"},
                "tags": [],
                "v": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_jsonl(path)

    assert records == [
        {
            "ts": "2026-03-04T10:00:00Z",
            "domain": "general",
            "kind": "note",
            "data": {"text": "v1 text"},
            "tags": [],
            "v": 1,
        }
    ]


def test_read_jsonl_prefers_data_text_when_data_and_payload_coexist(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "ts": "2026-03-04T10:00:00Z",
                "domain": "general",
                "data": {"text": "data wins"},
                "payload": {"text": "payload loses"},
                "tags": [],
                "v": 1,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_jsonl(path)

    assert records[0]["data"]["text"] == "data wins"
    assert records[0]["payload"]["text"] == "payload loses"


def test_read_jsonl_legacy_record_without_kind_keeps_kind_missing(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
    path.write_text(
        json.dumps(
            {
                "ts": "2026-03-04T10:00:00Z",
                "domain": "poe2",
                "payload": {"text": "x", "meta": {"source": "client_txt"}},
                "tags": [],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    records = read_jsonl(path)

    assert records[0]["data"]["text"] == "x"
    assert records[0]["source"] == "client_txt"
    assert "kind" not in records[0]
