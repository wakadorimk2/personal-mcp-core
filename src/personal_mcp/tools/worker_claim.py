from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional
import urllib.request


PROTOCOL_MARKER = "<!-- og-worker-claim:v1 -->"
PROTOCOL_NAME = "worker-claim/v1"
EVENT_TYPES = frozenset(
    {
        "claim",
        "release",
        "handoff_offer",
        "handoff_accept",
        "maintainer_override",
    }
)


def _normalize_required(value: str, *, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


def _normalize_optional(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _normalize_issue_number(value: int | str) -> int:
    if isinstance(value, int):
        if value <= 0:
            raise ValueError("issue_number must be positive")
        return value
    normalized = _normalize_required(value, field_name="issue_number")
    if normalized.startswith("#"):
        normalized = normalized[1:]
    if not normalized.isdigit():
        raise ValueError("issue_number must be numeric")
    issue_number = int(normalized)
    if issue_number <= 0:
        raise ValueError("issue_number must be positive")
    return issue_number


def _normalize_reason(reason: str) -> str:
    normalized = " ".join(reason.split())
    if not normalized:
        raise ValueError("reason must not be empty")
    return normalized


def _normalize_event_type(event_type: str) -> str:
    normalized = _normalize_required(event_type, field_name="event_type")
    if normalized not in EVENT_TYPES:
        raise ValueError(f"unsupported worker claim event_type: {normalized}")
    return normalized


def build_worker_claim_event(
    *,
    event_type: str,
    worker_id: str,
    runtime: str,
    issue_number: int | str,
    reason: str,
    ref: Optional[str] = None,
    target_worker_id: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_event_type = _normalize_event_type(event_type)
    event: Dict[str, Any] = {
        "protocol": PROTOCOL_NAME,
        "event_type": normalized_event_type,
        "worker_id": _normalize_required(worker_id, field_name="worker_id"),
        "runtime": _normalize_required(runtime, field_name="runtime"),
        "issue_number": _normalize_issue_number(issue_number),
        "reason": _normalize_reason(reason),
    }

    normalized_ref = _normalize_optional(ref)
    normalized_target_worker_id = _normalize_optional(target_worker_id)

    if normalized_event_type == "handoff_offer":
        if normalized_target_worker_id is None:
            raise ValueError("target_worker_id is required for handoff_offer")
        event["target_worker_id"] = normalized_target_worker_id
    elif normalized_target_worker_id is not None:
        raise ValueError(
            "target_worker_id is only allowed for "
            f"handoff_offer, got {normalized_event_type}"
        )

    if normalized_event_type == "claim":
        if normalized_ref is not None:
            raise ValueError("ref is not allowed for claim")
    else:
        if normalized_ref is None:
            raise ValueError(f"ref is required for {normalized_event_type}")
        event["ref"] = normalized_ref

    return event


def serialize_worker_claim_event(event: Dict[str, Any]) -> str:
    normalized_event = build_worker_claim_event(
        event_type=str(event.get("event_type", "")),
        worker_id=str(event.get("worker_id", "")),
        runtime=str(event.get("runtime", "")),
        issue_number=event.get("issue_number", ""),
        reason=str(event.get("reason", "")),
        ref=event.get("ref"),
        target_worker_id=event.get("target_worker_id"),
    )

    lines = [
        PROTOCOL_MARKER,
        f"protocol: {normalized_event['protocol']}",
        f"event_type: {normalized_event['event_type']}",
        f"worker_id: {normalized_event['worker_id']}",
        f"runtime: {normalized_event['runtime']}",
        f"issue_number: {normalized_event['issue_number']}",
        f"reason: {normalized_event['reason']}",
    ]
    if "ref" in normalized_event:
        lines.append(f"ref: {normalized_event['ref']}")
    if "target_worker_id" in normalized_event:
        lines.append(f"target_worker_id: {normalized_event['target_worker_id']}")
    return "\n".join(lines)


def parse_worker_claim_comment(body: str) -> Optional[Dict[str, Any]]:
    stripped = body.strip()
    if not stripped:
        return None

    lines = stripped.splitlines()
    if not lines or lines[0].strip() != PROTOCOL_MARKER:
        return None

    values: Dict[str, str] = {}
    for line in lines[1:]:
        if not line.strip():
            continue
        key, separator, raw_value = line.partition(":")
        if separator != ":":
            raise ValueError(f"invalid worker claim line: {line}")
        values[key.strip()] = raw_value.strip()
    if values.get("protocol") != PROTOCOL_NAME:
        raise ValueError(f"unsupported worker claim protocol: {values.get('protocol', '')}")

    return build_worker_claim_event(
        event_type=values.get("event_type", ""),
        worker_id=values.get("worker_id", ""),
        runtime=values.get("runtime", ""),
        issue_number=values.get("issue_number", ""),
        reason=values.get("reason", ""),
        ref=values.get("ref"),
        target_worker_id=values.get("target_worker_id"),
    )


def _parse_comment_timestamp(value: Any) -> datetime:
    if not isinstance(value, str) or not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _comment_order_key(comment: Dict[str, Any]) -> tuple[datetime, int]:
    comment_id = comment.get("id")
    numeric_id = comment_id if isinstance(comment_id, int) else -1
    return (_parse_comment_timestamp(comment.get("created_at")), numeric_id)


def _comment_id_as_ref(comment: Dict[str, Any]) -> str:
    comment_id = comment.get("id")
    if isinstance(comment_id, int):
        return str(comment_id)
    if isinstance(comment_id, str) and comment_id.strip():
        return comment_id.strip()
    raise ValueError("worker claim comment is missing id")


def _comment_actor_login(comment: Dict[str, Any]) -> Optional[str]:
    user = comment.get("user")
    if not isinstance(user, dict):
        return None
    login = user.get("login")
    if not isinstance(login, str):
        return None
    normalized = login.strip()
    return normalized or None


def derive_worker_claim_state(
    comments: list[Dict[str, Any]],
    *,
    issue_number: int | str,
    repo_owner: str,
) -> Dict[str, Any]:
    normalized_issue_number = _normalize_issue_number(issue_number)
    normalized_repo_owner = _normalize_required(repo_owner, field_name="repo_owner")

    state: Dict[str, Any] = {
        "state": "unclaimed",
        "owner": None,
        "claim_ref": None,
        "handoff_target_worker_id": None,
        "offer_ref": None,
        "events": [],
    }

    for comment in sorted(comments, key=_comment_order_key):
        body = comment.get("body")
        if not isinstance(body, str):
            continue

        parsed_event: Optional[Dict[str, Any]]
        invalid_reason: Optional[str] = None
        valid = False

        try:
            parsed_event = parse_worker_claim_comment(body)
        except ValueError as exc:
            parsed_event = None
            if body.strip().startswith(PROTOCOL_MARKER):
                invalid_reason = str(exc)
        if parsed_event is None:
            if invalid_reason is None:
                continue
        else:
            if parsed_event["issue_number"] != normalized_issue_number:
                invalid_reason = (
                    "issue_number does not match requested issue "
                    f"{normalized_issue_number}"
                )
            else:
                event_type = parsed_event["event_type"]
                event_ref = parsed_event.get("ref")
                current_state = state["state"]
                current_owner = state["owner"]
                claim_ref = state["claim_ref"]
                offer_ref = state["offer_ref"]
                target_worker_id = state["handoff_target_worker_id"]
                comment_ref = _comment_id_as_ref(comment)
                actor_login = _comment_actor_login(comment)

                if event_type == "claim":
                    if current_state == "unclaimed":
                        state["state"] = "claimed"
                        state["owner"] = parsed_event["worker_id"]
                        state["claim_ref"] = comment_ref
                        state["handoff_target_worker_id"] = None
                        state["offer_ref"] = None
                        valid = True
                    else:
                        invalid_reason = f"claim requires unclaimed state, got {current_state}"
                elif event_type == "release":
                    if current_state == "unclaimed":
                        invalid_reason = "release requires an active claim"
                    elif parsed_event["worker_id"] != current_owner:
                        invalid_reason = "release requires the current owner"
                    elif event_ref != claim_ref:
                        invalid_reason = f"release ref must match active claim ref {claim_ref}"
                    else:
                        state["state"] = "unclaimed"
                        state["owner"] = None
                        state["claim_ref"] = None
                        state["handoff_target_worker_id"] = None
                        state["offer_ref"] = None
                        valid = True
                elif event_type == "handoff_offer":
                    if current_state != "claimed":
                        invalid_reason = (
                            f"handoff_offer requires claimed state, got {current_state}"
                        )
                    elif parsed_event["worker_id"] != current_owner:
                        invalid_reason = "handoff_offer requires the current owner"
                    elif event_ref != claim_ref:
                        invalid_reason = (
                            f"handoff_offer ref must match active claim ref {claim_ref}"
                        )
                    else:
                        state["state"] = "handoff_pending"
                        state["handoff_target_worker_id"] = parsed_event["target_worker_id"]
                        state["offer_ref"] = comment_ref
                        valid = True
                elif event_type == "handoff_accept":
                    if current_state != "handoff_pending":
                        invalid_reason = (
                            f"handoff_accept requires handoff_pending state, got {current_state}"
                        )
                    elif parsed_event["worker_id"] != target_worker_id:
                        invalid_reason = "handoff_accept requires the handoff target worker"
                    elif event_ref != offer_ref:
                        invalid_reason = (
                            f"handoff_accept ref must match latest offer ref {offer_ref}"
                        )
                    else:
                        state["state"] = "claimed"
                        state["owner"] = parsed_event["worker_id"]
                        state["claim_ref"] = comment_ref
                        state["handoff_target_worker_id"] = None
                        state["offer_ref"] = None
                        valid = True
                elif event_type == "maintainer_override":
                    if current_state == "unclaimed":
                        invalid_reason = "maintainer_override requires an active claim or handoff"
                    elif actor_login != normalized_repo_owner:
                        invalid_reason = (
                            "maintainer_override requires the repository owner "
                            f"{normalized_repo_owner}"
                        )
                    else:
                        expected_ref = (
                            offer_ref if current_state == "handoff_pending" else claim_ref
                        )
                        if event_ref != expected_ref:
                            invalid_reason = (
                                "maintainer_override ref must match the current "
                                f"active ref {expected_ref}"
                            )
                        else:
                            state["state"] = "unclaimed"
                            state["owner"] = None
                            state["claim_ref"] = None
                            state["handoff_target_worker_id"] = None
                            state["offer_ref"] = None
                            valid = True

        state["events"].append(
            {
                "comment_id": comment.get("id"),
                "created_at": comment.get("created_at"),
                "actor_login": _comment_actor_login(comment),
                "valid": valid,
                "invalid_reason": invalid_reason,
                "event": parsed_event,
            }
        )

    return state


def _resolve_github_token(token: Optional[str]) -> str:
    resolved = _normalize_optional(token) or os.environ.get("GH_TOKEN") or os.environ.get(
        "GITHUB_TOKEN"
    )
    if not isinstance(resolved, str) or not resolved.strip():
        raise ValueError("GitHub token is required; set --token, GH_TOKEN, or GITHUB_TOKEN")
    return resolved.strip()


def _github_request_json(
    *,
    method: str,
    url: str,
    token: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Any:
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {token}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request) as response:
        body = response.read().decode("utf-8")
    return json.loads(body) if body else None


def fetch_issue_comments(
    *,
    owner: str,
    repo: str,
    issue_number: int | str,
    token: Optional[str] = None,
) -> list[Dict[str, Any]]:
    normalized_owner = _normalize_required(owner, field_name="owner")
    normalized_repo = _normalize_required(repo, field_name="repo")
    normalized_issue_number = _normalize_issue_number(issue_number)
    resolved_token = _resolve_github_token(token)

    comments: list[Dict[str, Any]] = []
    per_page = 100
    page = 1
    while True:
        page_url = (
            f"https://api.github.com/repos/{normalized_owner}/{normalized_repo}/issues/"
            f"{normalized_issue_number}/comments?per_page={per_page}&page={page}"
        )
        page_comments = _github_request_json(
            method="GET",
            url=page_url,
            token=resolved_token,
        )
        if not isinstance(page_comments, list):
            raise ValueError("GitHub issue comments response must be a list")
        comments.extend(page_comments)
        if len(page_comments) < per_page:
            break
        page += 1
    return comments


def worker_claim_state(
    *,
    owner: str,
    repo: str,
    issue_number: int | str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    comments = fetch_issue_comments(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        token=token,
    )
    return derive_worker_claim_state(
        comments,
        issue_number=issue_number,
        repo_owner=owner,
    )


def prepare_worker_claim_submission(
    *,
    owner: str,
    repo: str,
    issue_number: int | str,
    event_type: str,
    worker_id: str,
    runtime: str,
    reason: str,
    token: Optional[str] = None,
    ref: Optional[str] = None,
    target_worker_id: Optional[str] = None,
) -> Dict[str, Any]:
    state_before = worker_claim_state(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        token=token,
    )
    normalized_event_type = _normalize_event_type(event_type)
    normalized_ref = _normalize_optional(ref)

    if normalized_event_type == "claim":
        if state_before["state"] != "unclaimed":
            raise ValueError(f"claim requires unclaimed state, got {state_before['state']}")
    elif normalized_event_type == "release":
        if state_before["state"] == "unclaimed":
            raise ValueError("release requires an active claim")
        if state_before["owner"] != worker_id.strip():
            raise ValueError("release requires the current owner worker_id")
        normalized_ref = normalized_ref or state_before["claim_ref"]
    elif normalized_event_type == "handoff_offer":
        if state_before["state"] != "claimed":
            raise ValueError(f"handoff_offer requires claimed state, got {state_before['state']}")
        if state_before["owner"] != worker_id.strip():
            raise ValueError("handoff_offer requires the current owner worker_id")
        normalized_ref = normalized_ref or state_before["claim_ref"]
    elif normalized_event_type == "handoff_accept":
        if state_before["state"] != "handoff_pending":
            raise ValueError(
                f"handoff_accept requires handoff_pending state, got {state_before['state']}"
            )
        if state_before["handoff_target_worker_id"] != worker_id.strip():
            raise ValueError("handoff_accept requires the handoff target worker_id")
        normalized_ref = normalized_ref or state_before["offer_ref"]
    else:
        if state_before["state"] == "unclaimed":
            raise ValueError("maintainer_override requires an active claim or handoff")
        normalized_ref = normalized_ref or (
            state_before["offer_ref"]
            if state_before["state"] == "handoff_pending"
            else state_before["claim_ref"]
        )

    event = build_worker_claim_event(
        event_type=normalized_event_type,
        worker_id=worker_id,
        runtime=runtime,
        issue_number=issue_number,
        reason=reason,
        ref=normalized_ref,
        target_worker_id=target_worker_id,
    )
    return {
        "event": event,
        "comment_body": serialize_worker_claim_event(event),
        "state_before": state_before,
    }


def post_issue_comment(
    *,
    owner: str,
    repo: str,
    issue_number: int | str,
    body: str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_owner = _normalize_required(owner, field_name="owner")
    normalized_repo = _normalize_required(repo, field_name="repo")
    normalized_issue_number = _normalize_issue_number(issue_number)
    resolved_token = _resolve_github_token(token)
    normalized_body = _normalize_required(body, field_name="body")

    result = _github_request_json(
        method="POST",
        url=(
            f"https://api.github.com/repos/{normalized_owner}/{normalized_repo}/issues/"
            f"{normalized_issue_number}/comments"
        ),
        token=resolved_token,
        payload={"body": normalized_body},
    )
    if not isinstance(result, dict):
        raise ValueError("GitHub issue comment response must be an object")
    return result


def worker_claim_post(
    *,
    owner: str,
    repo: str,
    issue_number: int | str,
    event_type: str,
    worker_id: str,
    runtime: str,
    reason: str,
    token: Optional[str] = None,
    ref: Optional[str] = None,
    target_worker_id: Optional[str] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    prepared = prepare_worker_claim_submission(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        event_type=event_type,
        worker_id=worker_id,
        runtime=runtime,
        reason=reason,
        token=token,
        ref=ref,
        target_worker_id=target_worker_id,
    )
    result: Dict[str, Any] = {
        "event": prepared["event"],
        "comment_body": prepared["comment_body"],
        "state_before": prepared["state_before"],
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    comment = post_issue_comment(
        owner=owner,
        repo=repo,
        issue_number=issue_number,
        body=prepared["comment_body"],
        token=token,
    )
    result["comment"] = comment
    return result
