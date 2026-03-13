from __future__ import annotations

import pytest

import personal_mcp.tools.worker_claim as worker_claim_mod
from personal_mcp.tools.worker_claim import (
    PROTOCOL_MARKER,
    PROTOCOL_NAME,
    build_worker_claim_event,
    derive_worker_claim_state,
    fetch_issue_comments,
    parse_worker_claim_comment,
    post_issue_comment,
    prepare_worker_claim_submission,
    serialize_worker_claim_event,
    worker_claim_post,
)


def _comment(
    comment_id: int,
    body: str,
    *,
    created_at: str,
    login: str = "worker-bot",
) -> dict:
    return {
        "id": comment_id,
        "body": body,
        "created_at": created_at,
        "user": {"login": login},
    }


def test_build_worker_claim_event_normalizes_issue_and_reason() -> None:
    event = build_worker_claim_event(
        event_type="claim",
        worker_id=" codex-1 ",
        runtime=" codex ",
        issue_number="#378",
        reason="  draft   implementation  ",
    )

    assert event == {
        "protocol": PROTOCOL_NAME,
        "event_type": "claim",
        "worker_id": "codex-1",
        "runtime": "codex",
        "issue_number": 378,
        "reason": "draft implementation",
    }


def test_build_worker_claim_event_requires_ref_for_release() -> None:
    with pytest.raises(ValueError, match="ref is required for release"):
        build_worker_claim_event(
            event_type="release",
            worker_id="codex-1",
            runtime="codex",
            issue_number=378,
            reason="done",
        )


def test_build_worker_claim_event_requires_target_for_handoff_offer() -> None:
    with pytest.raises(ValueError, match="target_worker_id is required for handoff_offer"):
        build_worker_claim_event(
            event_type="handoff_offer",
            worker_id="codex-1",
            runtime="codex",
            issue_number=378,
            reason="needs docs review",
            ref="12345",
        )


def test_serialize_worker_claim_event_uses_stable_field_order() -> None:
    body = serialize_worker_claim_event(
        {
            "event_type": "handoff_offer",
            "worker_id": "codex-1",
            "runtime": "codex",
            "issue_number": 378,
            "reason": "needs docs review",
            "ref": "12345",
            "target_worker_id": "claude-1",
        }
    )

    assert body == "\n".join(
        [
            PROTOCOL_MARKER,
            "protocol: worker-claim/v1",
            "event_type: handoff_offer",
            "worker_id: codex-1",
            "runtime: codex",
            "issue_number: 378",
            "reason: needs docs review",
            "ref: 12345",
            "target_worker_id: claude-1",
        ]
    )


def test_parse_worker_claim_comment_round_trips_protocol_body() -> None:
    body = "\n".join(
        [
            PROTOCOL_MARKER,
            "protocol: worker-claim/v1",
            "event_type: handoff_accept",
            "worker_id: claude-1",
            "runtime: claude",
            "issue_number: 378",
            "reason: taking verification pass",
            "ref: 12346",
        ]
    )

    parsed = parse_worker_claim_comment(body)

    assert parsed == {
        "protocol": PROTOCOL_NAME,
        "event_type": "handoff_accept",
        "worker_id": "claude-1",
        "runtime": "claude",
        "issue_number": 378,
        "reason": "taking verification pass",
        "ref": "12346",
    }


def test_parse_worker_claim_comment_returns_none_for_non_protocol_comment() -> None:
    assert parse_worker_claim_comment("ordinary comment") is None


def test_parse_worker_claim_comment_rejects_invalid_lines() -> None:
    with pytest.raises(ValueError, match="invalid worker claim line"):
        parse_worker_claim_comment(f"{PROTOCOL_MARKER}\nprotocol worker-claim/v1")


def test_parse_worker_claim_comment_rejects_unknown_protocol() -> None:
    body = "\n".join(
        [
            PROTOCOL_MARKER,
            "protocol: worker-claim/v2",
            "event_type: claim",
            "worker_id: codex-1",
            "runtime: codex",
            "issue_number: 378",
            "reason: test",
        ]
    )

    with pytest.raises(ValueError, match="unsupported worker claim protocol"):
        parse_worker_claim_comment(body)


def test_derive_worker_claim_state_keeps_first_claim_on_conflict() -> None:
    comments = [
        _comment(
            101,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="claim",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="take issue",
                )
            ),
            created_at="2026-03-13T10:00:00Z",
        ),
        _comment(
            102,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="claim",
                    worker_id="claude-1",
                    runtime="claude",
                    issue_number=378,
                    reason="conflicting claim",
                )
            ),
            created_at="2026-03-13T10:01:00Z",
        ),
    ]

    state = derive_worker_claim_state(comments, issue_number=378, repo_owner="wakadorimk2")

    assert state["state"] == "claimed"
    assert state["owner"] == "codex-1"
    assert state["claim_ref"] == "101"
    assert state["events"][0]["valid"] is True
    assert state["events"][1]["valid"] is False


def test_derive_worker_claim_state_transfers_owner_on_handoff_accept() -> None:
    comments = [
        _comment(
            101,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="claim",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="take issue",
                )
            ),
            created_at="2026-03-13T10:00:00Z",
        ),
        _comment(
            102,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="handoff_offer",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="needs claude review",
                    ref="101",
                    target_worker_id="claude-1",
                )
            ),
            created_at="2026-03-13T10:01:00Z",
        ),
        _comment(
            103,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="handoff_accept",
                    worker_id="claude-1",
                    runtime="claude",
                    issue_number=378,
                    reason="taking review",
                    ref="102",
                )
            ),
            created_at="2026-03-13T10:02:00Z",
        ),
    ]

    state = derive_worker_claim_state(comments, issue_number=378, repo_owner="wakadorimk2")

    assert state["state"] == "claimed"
    assert state["owner"] == "claude-1"
    assert state["claim_ref"] == "103"
    assert all(event["valid"] is True for event in state["events"])


def test_derive_worker_claim_state_keeps_handoff_pending_on_wrong_accept() -> None:
    comments = [
        _comment(
            101,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="claim",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="take issue",
                )
            ),
            created_at="2026-03-13T10:00:00Z",
        ),
        _comment(
            102,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="handoff_offer",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="needs claude review",
                    ref="101",
                    target_worker_id="claude-1",
                )
            ),
            created_at="2026-03-13T10:01:00Z",
        ),
        _comment(
            103,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="handoff_accept",
                    worker_id="copilot-1",
                    runtime="copilot",
                    issue_number=378,
                    reason="incorrect accept",
                    ref="102",
                )
            ),
            created_at="2026-03-13T10:02:00Z",
        ),
    ]

    state = derive_worker_claim_state(comments, issue_number=378, repo_owner="wakadorimk2")

    assert state["state"] == "handoff_pending"
    assert state["owner"] == "codex-1"
    assert state["handoff_target_worker_id"] == "claude-1"
    assert state["offer_ref"] == "102"
    assert state["events"][2]["valid"] is False


def test_derive_worker_claim_state_allows_owner_release() -> None:
    comments = [
        _comment(
            101,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="claim",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="take issue",
                )
            ),
            created_at="2026-03-13T10:00:00Z",
        ),
        _comment(
            102,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="release",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="done",
                    ref="101",
                )
            ),
            created_at="2026-03-13T10:01:00Z",
        ),
    ]

    state = derive_worker_claim_state(comments, issue_number=378, repo_owner="wakadorimk2")

    assert state["state"] == "unclaimed"
    assert state["owner"] is None
    assert state["claim_ref"] is None
    assert all(event["valid"] is True for event in state["events"])


def test_derive_worker_claim_state_requires_repo_owner_for_override() -> None:
    comments = [
        _comment(
            101,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="claim",
                    worker_id="codex-1",
                    runtime="codex",
                    issue_number=378,
                    reason="take issue",
                )
            ),
            created_at="2026-03-13T10:00:00Z",
        ),
        _comment(
            102,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="maintainer_override",
                    worker_id="maintainer",
                    runtime="human",
                    issue_number=378,
                    reason="clear stale claim",
                    ref="101",
                )
            ),
            created_at="2026-03-13T10:01:00Z",
            login="outside-user",
        ),
        _comment(
            103,
            serialize_worker_claim_event(
                build_worker_claim_event(
                    event_type="maintainer_override",
                    worker_id="maintainer",
                    runtime="human",
                    issue_number=378,
                    reason="clear stale claim",
                    ref="101",
                )
            ),
            created_at="2026-03-13T10:02:00Z",
            login="wakadorimk2",
        ),
    ]

    state = derive_worker_claim_state(comments, issue_number=378, repo_owner="wakadorimk2")

    assert state["state"] == "unclaimed"
    assert state["events"][1]["valid"] is False
    assert state["events"][2]["valid"] is True


def test_fetch_issue_comments_paginates(monkeypatch) -> None:
    pages = [
        [{"id": 1, "body": "first"}] * 100,
        [{"id": 2, "body": "last"}],
    ]

    def fake_request_json(*, method: str, url: str, token: str, payload=None):
        assert method == "GET"
        assert token == "token"
        assert payload is None
        if "&page=1" in url:
            return pages[0]
        if "&page=2" in url:
            return pages[1]
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr(worker_claim_mod, "_github_request_json", fake_request_json)

    comments = fetch_issue_comments(
        owner="wakadorimk2",
        repo="orange-garden",
        issue_number=378,
        token="token",
    )

    assert len(comments) == 101
    assert comments[0]["id"] == 1
    assert comments[-1]["id"] == 2


def test_prepare_worker_claim_submission_infers_release_ref(monkeypatch) -> None:
    monkeypatch.setattr(
        worker_claim_mod,
        "worker_claim_state",
        lambda **kwargs: {
            "state": "claimed",
            "owner": "codex-1",
            "claim_ref": "101",
            "handoff_target_worker_id": None,
            "offer_ref": None,
            "events": [],
        },
    )

    prepared = prepare_worker_claim_submission(
        owner="wakadorimk2",
        repo="orange-garden",
        issue_number=378,
        event_type="release",
        worker_id="codex-1",
        runtime="codex",
        reason="done",
    )

    assert prepared["event"]["ref"] == "101"
    assert "ref: 101" in prepared["comment_body"]


def test_prepare_worker_claim_submission_infers_offer_ref_for_accept(monkeypatch) -> None:
    monkeypatch.setattr(
        worker_claim_mod,
        "worker_claim_state",
        lambda **kwargs: {
            "state": "handoff_pending",
            "owner": "codex-1",
            "claim_ref": "101",
            "handoff_target_worker_id": "claude-1",
            "offer_ref": "102",
            "events": [],
        },
    )

    prepared = prepare_worker_claim_submission(
        owner="wakadorimk2",
        repo="orange-garden",
        issue_number=378,
        event_type="handoff_accept",
        worker_id="claude-1",
        runtime="claude",
        reason="taking over",
    )

    assert prepared["event"]["ref"] == "102"


def test_post_issue_comment_sends_json_body(monkeypatch) -> None:
    captured: dict = {}

    def fake_request_json(*, method: str, url: str, token: str, payload=None):
        captured.update(
            {
                "method": method,
                "url": url,
                "token": token,
                "payload": payload,
            }
        )
        return {"id": 5001, "body": payload["body"]}

    monkeypatch.setattr(worker_claim_mod, "_github_request_json", fake_request_json)

    result = post_issue_comment(
        owner="wakadorimk2",
        repo="orange-garden",
        issue_number=378,
        body="test body",
        token="token",
    )

    assert result["id"] == 5001
    assert captured["method"] == "POST"
    assert captured["payload"] == {"body": "test body"}


def test_worker_claim_post_returns_dry_run_without_posting(monkeypatch) -> None:
    monkeypatch.setattr(
        worker_claim_mod,
        "prepare_worker_claim_submission",
        lambda **kwargs: {
            "event": {"event_type": "claim"},
            "comment_body": "protocol comment",
            "state_before": {"state": "unclaimed"},
        },
    )

    result = worker_claim_post(
        owner="wakadorimk2",
        repo="orange-garden",
        issue_number=378,
        event_type="claim",
        worker_id="codex-1",
        runtime="codex",
        reason="take issue",
        dry_run=True,
    )

    assert result == {
        "event": {"event_type": "claim"},
        "comment_body": "protocol comment",
        "state_before": {"state": "unclaimed"},
        "dry_run": True,
    }
