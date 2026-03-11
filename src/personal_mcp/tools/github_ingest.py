"""GitHub ingest — eng domain event ingest (Issue #247).

Responsibility boundary vs github_sync (#147):

  github_sync (#147) — existing manual-sync MVP
    - reads /users/{username}/events first page (up to 100)
    - minimal data.* payload: github_event_id only as extra field
    - dedup via storage boundary DB UNIQUE constraint on dedup_key

  github_ingest (#247) — full spec implementation (docs/eng-ingest-impl.md)
    - same /users/{username}/events endpoint
    - rich data.* payload per Section 3.3
    - dedup via storage boundary DB UNIQUE constraint on dedup_key
    - insert-only / skip per Section 3.4

Both use source="github" and data.github_event_id for dedup.
The storage boundary normalizes each event to a canonical dedup_key
("github:{github_event_id}") and enforces uniqueness via DB constraint.
Events saved by either tool share the same dedup key space.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Dict, List, Optional

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.events_store import append_event


_SKIP_TYPES: frozenset = frozenset({"WatchEvent", "PublicEvent", "MemberEvent"})


def _fetch_github_events(username: str, token: Optional[str]) -> List[Dict[str, Any]]:
    """Fetch user events from GitHub API (first page, up to 100)."""
    url = f"https://api.github.com/users/{username}/events?per_page=100"
    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def _normalize_ts(ts: str) -> str:
    """Normalize GitHub 'Z' suffix to explicit '+00:00' offset."""
    return ts.replace("Z", "+00:00")


def _map_github_event(gh_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a GitHub API event to an Event Contract v1 record.

    Implements:
      - Section 2.1/2.2/2.3 (target / fallback / exclusion)
      - Section 3.2 (ref format)
      - Section 3.3 (data.* minimum fields)
      - Section 4.2 (kind mapping)
    from docs/eng-ingest-impl.md.

    Returns None if the event should be skipped.
    """
    event_type = gh_event.get("type", "")
    if event_type in _SKIP_TYPES:
        return None

    payload = gh_event.get("payload", {})
    repo_full_name = gh_event.get("repo", {}).get("name", "")
    ts = _normalize_ts(gh_event.get("created_at", ""))
    event_id = str(gh_event.get("id", ""))
    action = payload.get("action", "")

    # Base data.* fields per Section 3.3
    extra_data: Dict[str, Any] = {
        "github_event_id": event_id,
        "github_event_type": event_type,
        "repo_full_name": repo_full_name,
    }
    if action:
        extra_data["action"] = action

    ref: Optional[str] = None
    kind: str = "note"
    text: str = ""

    if event_type == "PushEvent":
        commits = payload.get("commits", [])
        branch = payload.get("ref", "").replace("refs/heads/", "")
        commit_count = len(commits)
        head_sha = commits[0].get("sha", "") if commits else ""
        text = f"pushed {commit_count} commit(s) to {repo_full_name} ({branch})"
        kind = "artifact"
        if head_sha:
            ref = head_sha[:7]  # short SHA, 7 chars (Section 3.2)
            extra_data["head_sha"] = head_sha
        extra_data["commit_count"] = commit_count

    elif event_type == "IssuesEvent":
        issue = payload.get("issue", {})
        issue_number = issue.get("number", "")
        title = issue.get("title", "")
        ref = f"#{issue_number}"
        html_url = issue.get("html_url", "")
        if html_url:
            extra_data["html_url"] = html_url
        if action == "closed":
            text = f"closed issue: {title}"
            kind = "milestone"
        else:
            text = f"{action} issue: {title}"
            kind = "note"

    elif event_type == "PullRequestEvent":
        pr = payload.get("pull_request", {})
        pr_number = pr.get("number", "")
        title = pr.get("title", "")
        merged = pr.get("merged", False)
        ref = f"PR#{pr_number}"
        html_url = pr.get("html_url", "")
        if html_url:
            extra_data["html_url"] = html_url
        if action == "closed" and merged:
            text = f"merged PR: {title}"
            kind = "milestone"
        elif action == "closed":
            text = f"closed PR: {title}"
            kind = "milestone"
        else:
            text = f"{action} PR: {title}"
            kind = "artifact"

    elif event_type == "CreateEvent":
        ref_type = payload.get("ref_type", "")
        ref_name = payload.get("ref", "")
        text = f"created {ref_type}: {ref_name} on {repo_full_name}"
        kind = "artifact"
        extra_data["ref_type"] = ref_type
        extra_data["ref_name"] = ref_name
        # ref omitted for CreateEvent per Section 3.2

    else:
        # Fallback per Section 2.2: all three conditions must hold
        if not repo_full_name or not event_type:
            return None  # cannot generate stable data — skip
        text = f"{event_type} on {repo_full_name}"
        kind = "note"

    return build_v1_record(
        ts=ts,
        domain="eng",
        text=text,
        tags=[],
        kind=kind,
        source="github",
        ref=ref,
        extra_data=extra_data,
    )


def github_ingest(
    username: str,
    token: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, int]:
    """Fetch GitHub user events and append new ones via storage boundary.

    Implements the eng ingest spec (docs/eng-ingest-impl.md Section 2–5).
    Dedup is insert-only / skip per Section 3.4, enforced by DB UNIQUE
    constraint on dedup_key at the storage boundary; no pre-read is done.

    Returns {"saved": int, "skipped": int, "failed": int}.
    """
    try:
        gh_events = _fetch_github_events(username, token)
    except Exception:
        return {"saved": 0, "skipped": 0, "failed": 1}

    if not isinstance(gh_events, list):
        return {"saved": 0, "skipped": 0, "failed": 1}

    saved = skipped = failed = 0
    for gh_event in gh_events:
        try:
            record = _map_github_event(gh_event)
            if record is None:
                skipped += 1
                continue
            outcome = append_event(record, data_dir=data_dir)
            if outcome == "saved":
                saved += 1
            else:
                skipped += 1
        except Exception:
            failed += 1

    return {"saved": saved, "skipped": skipped, "failed": failed}
