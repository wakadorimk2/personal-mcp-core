from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from personal_mcp.server import main
from personal_mcp.storage.events_store import rebuild_db_from_jsonl, rebuild_jsonl_from_db
from personal_mcp.storage.sqlite import append_sqlite, read_sqlite


def _db_count(db_path: Path) -> int:
    with sqlite3.connect(str(db_path)) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])


def _write_events(path: Path, events: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def _insert_pre307_row(db_path: Path, record: dict) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        conn.executescript(
            """
            CREATE TABLE events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts TEXT NOT NULL,
                domain TEXT NOT NULL,
                kind TEXT,
                raw TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_events_ts ON events (ts);
            CREATE INDEX IF NOT EXISTS idx_events_domain ON events (domain);
            """
        )
        conn.execute(
            "INSERT INTO events (ts, domain, kind, raw) VALUES (?, ?, ?, ?)",
            (
                record["ts"],
                record["domain"],
                record["kind"],
                json.dumps(record, ensure_ascii=False),
            ),
        )
        conn.commit()


def test_rebuild_jsonl_from_db_dry_run_and_apply(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    jsonl_path = data_dir / "events.jsonl"
    append_sqlite(
        db_path,
        {
            "v": 1,
            "ts": "2026-03-08T00:00:00+00:00",
            "domain": "general",
            "kind": "note",
            "data": {"text": "from db 1"},
            "tags": [],
        },
    )
    append_sqlite(
        db_path,
        {
            "v": 1,
            "ts": "2026-03-08T01:00:00+00:00",
            "domain": "eng",
            "kind": "session",
            "data": {"text": "from db 2"},
            "tags": ["migration"],
        },
    )
    _write_events(
        jsonl_path,
        [
            {
                "v": 1,
                "ts": "2026-03-07T12:00:00+00:00",
                "domain": "mood",
                "kind": "note",
                "data": {"text": "old jsonl"},
                "tags": [],
            }
        ],
    )

    dry = rebuild_jsonl_from_db(data_dir=str(data_dir), dry_run=True)
    assert dry["source_count"] == 2
    assert dry["target_count"] == 1
    assert dry["count_diff"] == 1
    assert "written_count" not in dry
    assert len(jsonl_path.read_text(encoding="utf-8").splitlines()) == 1

    applied = rebuild_jsonl_from_db(data_dir=str(data_dir))
    assert applied["written_count"] == 2
    rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines()]
    assert [row["data"]["text"] for row in rows] == ["from db 1", "from db 2"]


def test_rebuild_db_from_jsonl_dry_run_and_apply_with_legacy_normalization(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    jsonl_path = data_dir / "events.jsonl"
    append_sqlite(
        db_path,
        {
            "v": 1,
            "ts": "2026-03-07T08:00:00+00:00",
            "domain": "general",
            "kind": "note",
            "data": {"text": "to be replaced"},
            "tags": [],
        },
    )
    _write_events(
        jsonl_path,
        [
            {
                "ts": "2026-03-08T02:00:00+00:00",
                "domain": "poe2",
                "payload": {"text": "legacy entry"},
                "tags": [],
            },
            {
                "v": 1,
                "ts": "2026-03-08T03:00:00+00:00",
                "domain": "worklog",
                "kind": "note",
                "data": {"text": "v1 entry"},
                "tags": [],
            },
        ],
    )

    dry = rebuild_db_from_jsonl(data_dir=str(data_dir), dry_run=True)
    assert dry["source_count"] == 2
    assert dry["target_count"] == 1
    assert dry["count_diff"] == 1
    assert _db_count(db_path) == 1

    applied = rebuild_db_from_jsonl(data_dir=str(data_dir))
    assert applied["written_count"] == 2
    rows = read_sqlite(db_path)
    assert len(rows) == 2
    assert rows[0]["data"]["text"] == "legacy entry"
    assert rows[1]["data"]["text"] == "v1 entry"


def test_append_sqlite_backfills_pre307_github_dedup_key(data_dir: Path) -> None:
    db_path = data_dir / "events.db"
    existing = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "already saved", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    _insert_pre307_row(db_path, existing)

    outcome = append_sqlite(db_path, existing)

    assert outcome == "skipped"
    assert len(read_sqlite(db_path)) == 1
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT id, dedup_key FROM events ORDER BY id ASC").fetchall()
    assert rows == [(1, "github:100")]


def test_rebuild_db_from_jsonl_reports_actual_written_count_after_dedup(
    data_dir: Path,
) -> None:
    duplicate = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "duplicate", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    manual = {
        "v": 1,
        "ts": "2026-03-07T11:00:00+00:00",
        "domain": "general",
        "kind": "note",
        "data": {"text": "manual"},
        "tags": [],
        "source": "manual",
    }
    _write_events(data_dir / "events.jsonl", [duplicate, duplicate, manual])

    applied = rebuild_db_from_jsonl(data_dir=str(data_dir))

    assert applied["source_count"] == 3
    assert applied["written_count"] == 2
    assert applied["skipped_count"] == 1
    assert len(read_sqlite(data_dir / "events.db")) == 2


def test_cli_storage_migration_dry_run_json_output(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    db_path = data_dir / "events.db"
    jsonl_path = data_dir / "events.jsonl"
    append_sqlite(
        db_path,
        {
            "v": 1,
            "ts": "2026-03-08T04:00:00+00:00",
            "domain": "general",
            "kind": "note",
            "data": {"text": "db record"},
            "tags": [],
        },
    )
    _write_events(
        jsonl_path,
        [
            {
                "v": 1,
                "ts": "2026-03-08T05:00:00+00:00",
                "domain": "general",
                "kind": "note",
                "data": {"text": "jsonl record"},
                "tags": [],
            }
        ],
    )

    rc_db_to_jsonl = main(
        ["storage-db-to-jsonl", "--dry-run", "--json", "--data-dir", str(data_dir)]
    )
    report_db_to_jsonl = json.loads(capsys.readouterr().out)
    assert rc_db_to_jsonl == 0
    assert report_db_to_jsonl["direction"] == "db_to_jsonl"
    assert report_db_to_jsonl["dry_run"] is True
    assert report_db_to_jsonl["source_count"] == 1

    rc_jsonl_to_db = main(
        ["storage-jsonl-to-db", "--dry-run", "--json", "--data-dir", str(data_dir)]
    )
    report_jsonl_to_db = json.loads(capsys.readouterr().out)
    assert rc_jsonl_to_db == 0
    assert report_jsonl_to_db["direction"] == "jsonl_to_db"
    assert report_jsonl_to_db["dry_run"] is True
    assert report_jsonl_to_db["source_count"] == 1


def test_cli_storage_db_to_jsonl_returns_error_when_source_missing(
    data_dir: Path, capsys: pytest.CaptureFixture
) -> None:
    rc = main(["storage-db-to-jsonl", "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    assert rc == 1
    assert "missing source file" in captured.out
