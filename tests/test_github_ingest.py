"""Regression tests for github_ingest (Issue #247).

Verifies:
- data.* fields per docs/eng-ingest-impl.md Section 3.3
- kind mapping per Section 4.2
- skip/exclusion per Section 2.3
- fallback conditions per Section 2.2
- ref format per Section 3.2
- dedup (insert-only/skip) per Section 3.4
- cross-dedup: events saved by github_sync are not re-ingested
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from personal_mcp.storage.events_store import append_event
from personal_mcp.tools.github_ingest import (
    _load_existing_github_event_ids,
    _map_github_event,
    _normalize_ts,
    github_ingest,
)


# ---------------------------------------------------------------------------
# fixtures / helpers
# ---------------------------------------------------------------------------


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
            "issue": {
                "number": 42,
                "title": "Fix the bug",
                "html_url": "https://github.com/user/repo/issues/42",
            },
        },
    }


def _pr_event(action: str = "closed", merged: bool = True, event_id: str = "300") -> Dict[str, Any]:
    return {
        "id": event_id,
        "type": "PullRequestEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T12:00:00Z",
        "payload": {
            "action": action,
            "pull_request": {
                "number": 7,
                "title": "Add feature",
                "merged": merged,
                "html_url": "https://github.com/user/repo/pull/7",
            },
        },
    }


def _create_event(event_id: str = "400") -> Dict[str, Any]:
    return {
        "id": event_id,
        "type": "CreateEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T13:00:00Z",
        "payload": {
            "ref_type": "branch",
            "ref": "feat/new-branch",
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


def _write_events(path: Path, events: list) -> None:
    path.write_text("\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# _normalize_ts
# ---------------------------------------------------------------------------


def test_normalize_ts_replaces_z() -> None:
    assert _normalize_ts("2026-03-07T10:00:00Z") == "2026-03-07T10:00:00+00:00"


def test_normalize_ts_leaves_explicit_offset_unchanged() -> None:
    ts = "2026-03-07T10:00:00+09:00"
    assert _normalize_ts(ts) == ts


# ---------------------------------------------------------------------------
# _map_github_event — Section 3.3 data.* fields
# ---------------------------------------------------------------------------


def test_map_push_event_includes_github_event_type() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["data"]["github_event_type"] == "PushEvent"


def test_map_push_event_includes_repo_full_name() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["data"]["repo_full_name"] == "user/repo"


def test_map_push_event_includes_head_sha() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["data"]["head_sha"] == "abc1234567890"


def test_map_push_event_includes_commit_count() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["data"]["commit_count"] == 1


def test_map_push_event_ref_is_7char_short_sha() -> None:
    """PushEvent ref is head commit short SHA (7 chars, Section 3.2)."""
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["ref"] == "abc1234"
    assert len(record["ref"]) == 7


def test_map_issues_event_includes_html_url() -> None:
    record = _map_github_event(_issues_event())
    assert record is not None
    assert record["data"]["html_url"] == "https://github.com/user/repo/issues/42"


def test_map_issues_event_includes_action() -> None:
    record = _map_github_event(_issues_event(action="opened"))
    assert record is not None
    assert record["data"]["action"] == "opened"


def test_map_pr_event_includes_html_url() -> None:
    record = _map_github_event(_pr_event())
    assert record is not None
    assert record["data"]["html_url"] == "https://github.com/user/repo/pull/7"


def test_map_pr_event_includes_action() -> None:
    record = _map_github_event(_pr_event(action="opened", merged=False))
    assert record is not None
    assert record["data"]["action"] == "opened"


def test_map_create_event_includes_ref_type_and_name() -> None:
    record = _map_github_event(_create_event())
    assert record is not None
    assert record["data"]["ref_type"] == "branch"
    assert record["data"]["ref_name"] == "feat/new-branch"


def test_map_create_event_omits_ref_field() -> None:
    """CreateEvent ref is omitted per Section 3.2."""
    record = _map_github_event(_create_event())
    assert record is not None
    assert "ref" not in record


# ---------------------------------------------------------------------------
# _map_github_event — Section 4.2 kind mapping
# ---------------------------------------------------------------------------


def test_map_push_event_kind_is_artifact() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["kind"] == "artifact"


def test_map_issue_closed_kind_is_milestone() -> None:
    record = _map_github_event(_issues_event(action="closed"))
    assert record is not None
    assert record["kind"] == "milestone"
    assert record["ref"] == "#42"


def test_map_issue_opened_kind_is_note() -> None:
    record = _map_github_event(_issues_event(action="opened"))
    assert record is not None
    assert record["kind"] == "note"


def test_map_pr_merged_kind_is_milestone() -> None:
    record = _map_github_event(_pr_event(action="closed", merged=True))
    assert record is not None
    assert record["kind"] == "milestone"
    assert "merged" in record["data"]["text"]
    assert record["ref"] == "PR#7"


def test_map_pr_closed_not_merged_kind_is_milestone() -> None:
    record = _map_github_event(_pr_event(action="closed", merged=False))
    assert record is not None
    assert record["kind"] == "milestone"


def test_map_pr_opened_kind_is_artifact() -> None:
    record = _map_github_event(_pr_event(action="opened", merged=False))
    assert record is not None
    assert record["kind"] == "artifact"


def test_map_create_event_kind_is_artifact() -> None:
    record = _map_github_event(_create_event())
    assert record is not None
    assert record["kind"] == "artifact"


# ---------------------------------------------------------------------------
# _map_github_event — Section 3.1 source / domain / contract
# ---------------------------------------------------------------------------


def test_map_event_domain_is_eng() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["domain"] == "eng"


def test_map_event_source_is_github() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["source"] == "github"


def test_map_event_is_v1() -> None:
    record = _map_github_event(_push_event())
    assert record is not None
    assert record["v"] == 1


# ---------------------------------------------------------------------------
# _map_github_event — Section 2.3 skip (exclusion list)
# ---------------------------------------------------------------------------


def test_map_watch_event_returns_none() -> None:
    assert _map_github_event(_watch_event()) is None


def test_map_public_event_returns_none() -> None:
    gh: Dict[str, Any] = {
        "id": "1",
        "type": "PublicEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T10:00:00Z",
        "payload": {},
    }
    assert _map_github_event(gh) is None


def test_map_member_event_returns_none() -> None:
    gh: Dict[str, Any] = {
        "id": "1",
        "type": "MemberEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T10:00:00Z",
        "payload": {},
    }
    assert _map_github_event(gh) is None


# ---------------------------------------------------------------------------
# _map_github_event — Section 2.2 fallback conditions
# ---------------------------------------------------------------------------


def test_map_fallback_unknown_type_with_repo_returns_note() -> None:
    gh: Dict[str, Any] = {
        "id": "1",
        "type": "ForkEvent",
        "repo": {"name": "user/repo"},
        "created_at": "2026-03-07T10:00:00Z",
        "payload": {},
    }
    record = _map_github_event(gh)
    assert record is not None
    assert record["kind"] == "note"
    assert record["data"]["github_event_type"] == "ForkEvent"
    assert record["data"]["repo_full_name"] == "user/repo"


def test_map_fallback_without_repo_returns_none() -> None:
    """Fallback skip: repo_full_name missing — Section 2.2 condition not met."""
    gh: Dict[str, Any] = {
        "id": "1",
        "type": "ForkEvent",
        "repo": {"name": ""},
        "created_at": "2026-03-07T10:00:00Z",
        "payload": {},
    }
    assert _map_github_event(gh) is None


# ---------------------------------------------------------------------------
# _load_existing_github_event_ids
# ---------------------------------------------------------------------------


def test_load_ids_returns_empty_when_no_events(data_dir: Path) -> None:
    assert _load_existing_github_event_ids(str(data_dir)) == set()


def test_load_ids_returns_github_source_ids(data_dir: Path) -> None:
    path = data_dir / "events.jsonl"
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
        "data": {"text": "manual"},
        "tags": [],
        "source": "manual",
    }
    _write_events(path, [github_event, manual_event])
    assert _load_existing_github_event_ids(str(data_dir)) == {"abc"}


def test_load_ids_includes_jsonl_only_github_rows_when_db_has_other_rows(
    data_dir: Path,
) -> None:
    append_event(
        {
            "v": 1,
            "ts": "2026-03-07T10:00:00+00:00",
            "domain": "general",
            "kind": "note",
            "data": {"text": "db row"},
            "tags": [],
            "source": "manual",
        },
        data_dir=str(data_dir),
    )
    path = data_dir / "events.jsonl"
    manual_event = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "general",
        "kind": "note",
        "data": {"text": "db row"},
        "tags": [],
        "source": "manual",
    }
    github_jsonl_only = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "legacy", "github_event_id": "abc"},
        "tags": [],
        "source": "github",
    }
    _write_events(path, [manual_event, github_jsonl_only])

    assert _load_existing_github_event_ids(str(data_dir)) == {"abc"}


# ---------------------------------------------------------------------------
# github_ingest — integration (Section 3.4: insert-only / skip)
# ---------------------------------------------------------------------------


def test_github_ingest_saves_new_event(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result == {"saved": 1, "skipped": 0, "failed": 0}
    lines = (data_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    saved = json.loads(lines[0])
    assert saved["data"]["github_event_id"] == "100"
    assert saved["data"]["github_event_type"] == "PushEvent"
    assert saved["data"]["repo_full_name"] == "user/repo"


def test_github_ingest_skips_duplicate(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod

    path = data_dir / "events.jsonl"
    existing = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "already saved", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    _write_events(path, [existing])
    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result["saved"] == 0
    assert result["skipped"] == 1
    # File must still have exactly the pre-existing record (no new append)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_github_ingest_skips_event_already_saved_by_github_sync(
    data_dir: Path,
    monkeypatch,
) -> None:
    """Events saved by github_sync (#147) must not be re-ingested (cross-dedup regression)."""
    import personal_mcp.tools.github_ingest as mod

    # Simulate github_sync having previously saved this event (minimal data.* payload)
    path = data_dir / "events.jsonl"
    github_sync_record = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "pushed 1 commit(s) to user/repo (main)", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    _write_events(path, [github_sync_record])
    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result["saved"] == 0
    assert result["skipped"] == 1
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1


def test_github_ingest_skips_duplicate_when_id_exists_only_in_jsonl(
    data_dir: Path,
    monkeypatch,
) -> None:
    import personal_mcp.tools.github_ingest as mod

    append_event(
        {
            "v": 1,
            "ts": "2026-03-07T10:00:00+00:00",
            "domain": "general",
            "kind": "note",
            "data": {"text": "db row"},
            "tags": [],
            "source": "manual",
        },
        data_dir=str(data_dir),
    )
    path = data_dir / "events.jsonl"
    manual_event = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "general",
        "kind": "note",
        "data": {"text": "db row"},
        "tags": [],
        "source": "manual",
    }
    github_sync_record = {
        "v": 1,
        "ts": "2026-03-07T10:00:00+00:00",
        "domain": "eng",
        "kind": "artifact",
        "data": {"text": "legacy", "github_event_id": "100"},
        "tags": [],
        "source": "github",
    }
    _write_events(path, [manual_event, github_sync_record])
    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result == {"saved": 0, "skipped": 1, "failed": 0}
    assert len(path.read_text(encoding="utf-8").splitlines()) == 2


def test_github_ingest_skips_low_signal_event(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_watch_event()])

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result["saved"] == 0
    assert result["skipped"] == 1


def test_github_ingest_summary_counts(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod

    monkeypatch.setattr(
        mod,
        "_fetch_github_events",
        lambda u, t: [
            _push_event("100"),
            _issues_event("closed", "200"),
            _watch_event("999"),
        ],
    )

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result == {"saved": 2, "skipped": 1, "failed": 0}


def test_github_ingest_handles_fetch_exception(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod

    def _raise(u, t):
        raise RuntimeError("connection failed")

    monkeypatch.setattr(mod, "_fetch_github_events", _raise)

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result == {"saved": 0, "skipped": 0, "failed": 1}


def test_github_ingest_handles_non_list_api_response(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: {"message": "Bad credentials"})

    result = github_ingest(username="user", data_dir=str(data_dir))

    assert result == {"saved": 0, "skipped": 0, "failed": 1}


def test_cli_github_ingest_json_output(data_dir: Path, monkeypatch, capsys) -> None:
    import personal_mcp.tools.github_ingest as mod
    from personal_mcp.server import main

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])
    main(["github-ingest", "--username", "user", "--data-dir", str(data_dir), "--json"])

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["saved"] == 1
    assert result["skipped"] == 0
    assert result["failed"] == 0


def test_cli_github_ingest_text_output(data_dir: Path, monkeypatch, capsys) -> None:
    import personal_mcp.tools.github_ingest as mod
    from personal_mcp.server import main

    monkeypatch.setattr(mod, "_fetch_github_events", lambda u, t: [_push_event("100")])
    main(["github-ingest", "--username", "user", "--data-dir", str(data_dir)])

    captured = capsys.readouterr()
    assert "saved: 1" in captured.out
    assert "skipped: 0" in captured.out
    assert "failed: 0" in captured.out


def test_cli_github_ingest_env_token_used(data_dir: Path, monkeypatch) -> None:
    import personal_mcp.tools.github_ingest as mod
    from personal_mcp.server import main

    captured_token: Dict[str, Any] = {}

    def _capture(u, t):
        captured_token["token"] = t
        return []

    monkeypatch.setattr(mod, "_fetch_github_events", _capture)
    monkeypatch.setenv("GITHUB_TOKEN", "env-token-xyz")
    main(["github-ingest", "--username", "user", "--data-dir", str(data_dir)])

    assert captured_token["token"] == "env-token-xyz"


def test_cli_github_ingest_explicit_token_overrides_env(
    data_dir: Path,
    monkeypatch,
) -> None:
    import personal_mcp.tools.github_ingest as mod
    from personal_mcp.server import main

    captured_token: Dict[str, Any] = {}

    def _capture(u, t):
        captured_token["token"] = t
        return []

    monkeypatch.setattr(mod, "_fetch_github_events", _capture)
    monkeypatch.setenv("GITHUB_TOKEN", "env-token")
    main(
        [
            "github-ingest",
            "--username",
            "user",
            "--token",
            "tok",
            "--data-dir",
            str(data_dir),
        ]
    )

    assert captured_token["token"] == "tok"
