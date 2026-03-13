from __future__ import annotations

import json

import personal_mcp.server as server


def test_main_worker_claim_state_json(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        server,
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

    exit_code = server.main(
        [
            "worker-claim-state",
            "--owner",
            "wakadorimk2",
            "--repo",
            "orange-garden",
            "--issue-number",
            "378",
            "--json",
        ]
    )

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    assert output["state"] == "claimed"
    assert output["owner"] == "codex-1"


def test_main_worker_claim_post_prints_comment_body(capsys, monkeypatch) -> None:
    monkeypatch.setattr(
        server,
        "worker_claim_post",
        lambda **kwargs: {
            "event": {"event_type": "claim"},
            "comment_body": "<!-- og-worker-claim:v1 -->\nprotocol: worker-claim/v1",
            "state_before": {"state": "unclaimed"},
            "dry_run": True,
        },
    )

    exit_code = server.main(
        [
            "worker-claim-post",
            "--owner",
            "wakadorimk2",
            "--repo",
            "orange-garden",
            "--issue-number",
            "378",
            "--event-type",
            "claim",
            "--worker-id",
            "codex-1",
            "--runtime",
            "codex",
            "--reason",
            "take issue",
            "--dry-run",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "<!-- og-worker-claim:v1 -->" in output
    assert "protocol: worker-claim/v1" in output
