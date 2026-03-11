from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from personal_mcp.storage.events_store import append_event
from personal_mcp.storage.sqlite import read_sqlite
from personal_mcp.tools.github_sync import (
    _load_existing_github_event_ids,
    _map_event_to_record,
    _normalize_ts,
    github_sync,
)


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------


def _read_runtime_events(data_dir: Path) -> list[dict]:
    return read_sqlite(data_dir / "events.db")


def _push_event(event_id: str = "100") -> Dict[str, Any]:
    return {
        "id": event_id,
        "type": "PushEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T10:00:00Z",
        "payload": {
            "ref": "refs/heads/main",
            "commits": [{"sha": "abc1234567890"}],
        },
    }


def _issues_event(action: str = "closed", event_id: str = "200") -> Dict[str, Any]:
    return {
        "id": event_id,
        "type": "IssuesEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T11:00:00Z",
        "payload": {
            "action": action,
            "issue": {"number": 42, "title": "Fix the bug"},
        },
    }


def _watch_event(event_id: str = "999") -> Dict[str, Any]:
    return {
        "id": event_id,
        "type": "WatchEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T10:00:00Z",
        "payload": {},
    }


# ---------------------------------------------------------------------------
# _normalize_ts
# ---------------------------------------------------------------------------


def test_normalize_ts_replaces_z() -> None:
    assert _normalize_ts("2026-03-07T10:00:00Z") == "2026-03-07T10:00:00+00:00"


def test_normalize_ts_leaves_explicit_offset_unchanged() -> None:
    ts = "2026-03-07T10:00:00+09:00"
    assert _normalize_ts(ts) == ts


# ---------------------------------------------------------------------------
# _map_event_to_record (FR-02)
# ---------------------------------------------------------------------------


def test_map_push_event_produces_v1_record() -> None:
    record = _map_event_to_record(_push_event())
    assert record is not None
    assert record["v"] == 1
    assert record["domain"] == "eng"
    assert record["kind"] == "artifact"
    assert record["source"] == "github"
    assert "pushed" in record["data"]["text"]
    assert record["data"]["github_event_id"] == "100"
    assert record["ref"] == "abc1234"
    assert record["ts"] == "2026-03-07T10:00:00+00:00"


def test_map_issue_closed_is_milestone() -> None:
    record = _map_event_to_record(_issues_event(action="closed"))
    assert record is not None
    assert record["kind"] == "milestone"
    assert record["ref"] == "#42"
    assert "closed" in record["data"]["text"]
    assert "Fix the bug" in record["data"]["text"]


def test_map_issue_opened_is_note() -> None:
    record = _map_event_to_record(_issues_event(action="opened"))
    assert record is not None
    assert record["kind"] == "note"


def test_map_pr_merged_is_milestone() -> None:
    gh = {
        "id": "300",
        "type": "PullRequestEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T12:00:00Z",
        "payload": {
            "action": "closed",
            "pull_request": {"number": 7, "title": "Add feature", "merged": True},
        },
    }
    record = _map_event_to_record(gh)
    assert record is not None
    assert record["kind"] == "milestone"
    assert record["ref"] == "PR#7"
    assert "merged" in record["data"]["text"]


def test_map_watch_event_returns_none() -> None:
    assert _map_event_to_record(_watch_event()) is None


# ---------------------------------------------------------------------------
# _load_existing_github_event_ids
# ---------------------------------------------------------------------------


def test_load_ids_returns_empty_when_file_missing(data_dir: Path) -> None:
    assert _load_existing_github_event_ids(str(data_dir)) == set()


def test_load_ids_returns_only_github_source_ids(data_dir: Path) -> None:
    github_event = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "x", "github_event_id": "abc"},
        "tags": [],
        "source": "github",
    }
    manual_event = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "note",
        "data": {"text": "manual entry"},
        "tags": [],
        "source": "manual",
    }
    append_event(github_event, data_dir=str(data_dir))
    append_event(manual_event, data_dir=str(data_dir))
    assert _load_existing_github_event_ids(str(data_dir)) == {"abc"}


# ---------------------------------------------------------------------------
# github_sync (FR-01, FR-03, FR-04)
# ---------------------------------------------------------------------------


def test_github_sync_saves_new_event(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_sync as mod

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result == {"saved": 1, "skipped": 0, "failed": 0}
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    assert rows[0]["data"]["github_event_id"] == "100"


def test_github_sync_skips_duplicate(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_sync as mod

    existing = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "already saved", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    append_event(existing, data_dir=str(data_dir))
    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result["saved"] == 0
    assert result["skipped"] == 1
    assert len(_read_runtime_events(data_dir)) == 1


def test_github_sync_skips_duplicate_when_id_exists_only_in_db(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_sync as mod

    append_only_db_record = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "already saved", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    append_event(append_only_db_record, data_dir=str(data_dir))
    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result["saved"] == 0
    assert result["skipped"] == 1
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1


def test_github_sync_skips_low_signal_event(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_sync as mod

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_watch_event()])

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result["saved"] == 0
    assert result["skipped"] == 1
    assert not (data_dir / "events.jsonl").exists()


def test_github_sync_summary_counts(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_sync as mod

    monkeypatch.setattr(
        mod,
        "_fetch_github_events",
        lambda u, t: [
            _push_event("100"),
            _issues_event("closed", "200"),
            _watch_event("999"),
        ],
    )

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result == {"saved": 2, "skipped": 1, "failed": 0}


# ---------------------------------------------------------------------------
# github_sync: API エラー応答・fetch 失敗の防御 (HIGH finding)
# ---------------------------------------------------------------------------


def test_github_sync_handles_non_list_api_response(data_dir: Path, monkeypatch) -> None:
    """API が dict を返した場合（Bad credentials 等）にクラッシュしない。"""
    import personal_mcp.tools.github_sync as mod

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: {"message": "Bad credentials"})

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result == {"saved": 0, "skipped": 0, "failed": 1}
    assert not (data_dir / "events.jsonl").exists()


def test_github_sync_handles_fetch_exception(data_dir: Path, monkeypatch) -> None:
    """_fetch_github_events が例外を投げた場合にクラッシュしない。"""
    import personal_mcp.tools.github_sync as mod

    def _raise(u, t):
        raise RuntimeError("connection failed")

    monkeypatch.setattr(mod, "_fetch_github_events", _raise)

    result = github_sync(username="user", data_dir=str(data_dir))

    assert result == {"saved": 0, "skipped": 0, "failed": 1}


# ---------------------------------------------------------------------------
# CLI integration via server.main (--json output, token priority)
# ---------------------------------------------------------------------------


def test_cli_github_sync_json_output(data_dir: Path, monkeypatch, capsys) -> None:
    """--json flag outputs parseable JSON summary."""
    import personal_mcp.tools.github_sync as mod
    from personal_mcp.server import main

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])
    main(["github-sync", "--username", "user", "--data-dir", str(data_dir), "--json"])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["saved"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0


def test_cli_github_sync_text_output(data_dir: Path, monkeypatch, capsys) -> None:
    """Text output shows saved/skipped/failed counts."""
    import personal_mcp.tools.github_sync as mod
    from personal_mcp.server import main

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])
    main(["github-sync", "--username", "user", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert "saved: 1" in captured.out
    assert "skipped: 0" in captured.out
    assert "failed: 0" in captured.out


def test_cli_github_sync_env_token_used(data_dir: Path, monkeypatch) -> None:
    """GITHUB_TOKEN env var is passed to fetch when --token is omitted."""
    import personal_mcp.tools.github_sync as mod
    from personal_mcp.server import main

    captured_token: Dict[str, Any] = {}

    def _capture(u, t):
        captured_token["token"] = t
        return []

    monkeypatch.setattr(mod, "_fetch_github_events", _capture)
    monkeypatch.setenv("GITHUB_TOKEN", "env-token-xyz")
    main(["github-sync", "--username", "user", "--data-dir", str(data_dir)])

    assert captured_token["token"] == "env-token-xyz"


def test_cli_github_sync_explicit_token_overrides_env(data_dir: Path, monkeypatch) -> None:
    """--token takes precedence over GITHUB_TOKEN env var."""
    import personal_mcp.tools.github_sync as mod
    from personal_mcp.server import main

    captured_token: Dict[str, Any] = {}

    def _capture(u, t):
        captured_token["token"] = t
        return []

    monkeypatch.setattr(mod, "_fetch_github_events", _capture)
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    main(["github-sync", "--username", "user", "--token", "tok", "--data-dir", str(data_dir)])

    assert captured_token["token"] == "tok"
