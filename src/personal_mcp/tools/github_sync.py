from __future__ import annotations

import json
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from personal_mcp.core.event import build_v1_record
from personal_mcp.storage.jsonl import append_jsonl, read_jsonl
from personal_mcp.storage.path import resolve_data_dir


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


def _map_event_to_record(gh_event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Map a GitHub API event to an Event Contract v1 record.

    Returns None for event types that should be skipped.
    """
    event_type = gh_event.get("type", "")
    if event_type in _SKIP_TYPES:
        return None

    payload = gh_event.get("payload", {})
    repo = gh_event.get("repo", {}).get("name", "")
    ts = _normalize_ts(gh_event.get("created_at", ""))
    event_id = str(gh_event.get("id", ""))

    extra_data: Dict[str, Any] = {"github_event_id": event_id}
    ref: Optional[str] = None
    kind: str = "note"
    text: str = ""

    if event_type == "PushEvent":
        commits = payload.get("commits", [])
        branch = payload.get("ref", "").replace("refs/heads/", "")
        text = f"pushed {len(commits)} commit(s) to {repo} ({branch})"
        kind = "artifact"
        if commits:
            ref = commits[0].get("sha", "")[:7]
    elif event_type == "IssuesEvent":
        action = payload.get("action", "")
        issue = payload.get("issue", {})
        ref = f"#{issue.get('number', '')}"
        text = f"{action} issue: {issue.get('title', '')}"
        kind = "milestone" if action == "closed" else "note"
    elif event_type == "PullRequestEvent":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        ref = f"PR#{pr.get('number', '')}"
        merged = pr.get("merged", False)
        title = pr.get("title", "")
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
        text = f"created {ref_type}: {ref_name} on {repo}"
        kind = "artifact"
    else:
        text = f"{event_type} on {repo}"
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


def _load_existing_github_event_ids(path: Path) -> Set[str]:
    """Return the set of github_event_id values already stored."""
    if not path.exists():
        return set()
    ids: Set[str] = set()
    for r in read_jsonl(path):
        if r.get("source") == "github":
            eid = r.get("data", {}).get("github_event_id")
            if eid:
                ids.add(str(eid))
    return ids


def github_sync(
    username: str,
    token: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, int]:
    """Fetch GitHub user events and append new ones to events.jsonl.

    Returns {"saved": int, "skipped": int, "failed": int}.
    """
    resolved = resolve_data_dir(data_dir)
    path = Path(resolved) / "events.jsonl"

    existing_ids = _load_existing_github_event_ids(path)
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
            record = _map_event_to_record(gh_event)
            if record is None:
                skipped += 1
                continue
            append_jsonl(path, record)
            existing_ids.add(event_id)
            saved += 1
        except Exception:
            failed += 1

    return {"saved": saved, "skipped": skipped, "failed": failed}
