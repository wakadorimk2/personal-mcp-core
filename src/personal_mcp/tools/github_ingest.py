"""GitHub ingest — eng domain event ingest (Issue #247).

Responsibility boundary vs github_sync (#147):

  github_sync (#147) — existing manual-sync MVP
    - reads /users/{username}/events first page (up to 100)
    - minimal data.* payload: github_event_id only as extra field
    - dedup reads events.jsonl directly (storage.jsonl layer)

  github_ingest (#247) — full spec implementation (docs/eng-ingest-impl.md)
    - same /users/{username}/events endpoint
    - rich data.* payload per Section 3.3
    - storage-layer-agnostic dedup via read_events() (events_store boundary)
    - insert-only / skip per Section 3.4

Both use source="github" and data.github_event_id for dedup.
Events saved by either tool share the same dedup key space.
"""

from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.events_store import append_event
from personal_mcp.storage.jsonl import read_jsonl
from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import read_sqlite


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


def _load_existing_github_event_ids(data_dir: Optional[str]) -> Set[str]:
    """Return github_event_id values already stored across current storages.

    During dual-write migration, older github records may exist only in
    events.jsonl even when events.db is non-empty. Read both backends and
    union ids so insert-only / skip remains stable across mixed storage.
    """
    resolved = Path(resolve_data_dir(data_dir))
    db_path = resolved / "events.db"
    jsonl_path = resolved / "events.jsonl"
    ids: Set[str] = set()
    for rows in (read_sqlite(db_path), read_jsonl(jsonl_path)):
        for r in rows:
            if r.get("source") == "github":
                eid = r.get("data", {}).get("github_event_id")
                if eid:
                    ids.add(str(eid))
    return ids


def github_ingest(
    username: str,
    token: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, int]:
    """Fetch GitHub user events and append new ones via storage boundary.

    Implements the eng ingest spec (docs/eng-ingest-impl.md Section 2–5).
    Dedup is insert-only / skip per Section 3.4.

    Returns {"saved": int, "skipped": int, "failed": int}.
    """
    existing_ids = _load_existing_github_event_ids(data_dir)
    try:
        gh_events = _fetch_github_events(username, token)
    except Exception:
        return {"saved": 0, "skipped": 0, "failed": 1}

    if not isinstance(gh_events, list):
        return {"saved": 0, "skipped": 0, "failed": 1}

    saved = skipped = failed = 0
    for gh_event in gh_events:
        event_id = str(gh_event.get("id", ""))
        if event_id in existing_ids:
            skipped += 1
            continue
        try:
            record = _map_github_event(gh_event)
            if record is None:
                skipped += 1
                continue
            append_event(record, data_dir=data_dir)
            existing_ids.add(event_id)
            saved += 1
        except Exception:
            failed += 1

    return {"saved": saved, "skipped": skipped, "failed": failed}
