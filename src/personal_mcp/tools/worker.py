from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from personal_mcp.storage.events_store import read_events
from personal_mcp.tools.event import event_add


ALLOWED_WORKER_STATUSES = frozenset({"working", "waiting", "reviewing", "idle", "done"})
CURRENT_ISSUE_SOURCE = "registry_hint"
OWNERSHIP_SOURCE = "github_issue"


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


def _normalize_issue(current_issue: Optional[str]) -> Optional[str]:
    normalized = _normalize_optional(current_issue)
    if normalized is None:
        return None
    if normalized.isdigit():
        return f"#{normalized}"
    return normalized


def _format_status_text(worker_name: str, status: str, current_issue: Optional[str]) -> str:
    if current_issue:
        return f"{worker_name} is {status} on {current_issue}"
    return f"{worker_name} is {status}"


def _parse_ts(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def worker_status_set(
    *,
    worker_id: str,
    worker_name: Optional[str],
    terminal_id: str,
    current_issue: Optional[str],
    status: str,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    normalized_worker_id = _normalize_required(worker_id, field_name="worker_id")
    normalized_terminal_id = _normalize_required(terminal_id, field_name="terminal_id")
    normalized_status = _normalize_required(status, field_name="status")
    if normalized_status not in ALLOWED_WORKER_STATUSES:
        raise ValueError(f"unsupported worker status: {normalized_status}")

    normalized_worker_name = _normalize_optional(worker_name) or normalized_worker_id
    normalized_issue = _normalize_issue(current_issue)

    meta: Dict[str, Any] = {
        "worker_id": normalized_worker_id,
        "worker_name": normalized_worker_name,
        "terminal_id": normalized_terminal_id,
        "status": normalized_status,
        "source": "worker-cli",
    }
    if normalized_issue is not None:
        meta["current_issue"] = normalized_issue

    return event_add(
        domain="worker",
        text=_format_status_text(normalized_worker_name, normalized_status, normalized_issue),
        kind="milestone",
        tags=[normalized_status],
        meta=meta,
        data_dir=data_dir,
    )


def worker_board_rows(data_dir: Optional[str] = None) -> List[Dict[str, Any]]:
    latest_by_worker: Dict[str, Dict[str, Any]] = {}
    for record in read_events(data_dir=data_dir):
        if record.get("domain") != "worker" or record.get("kind") != "milestone":
            continue
        data = record.get("data")
        if not isinstance(data, dict):
            continue

        worker_id = data.get("worker_id")
        worker_name = data.get("worker_name")
        terminal_id = data.get("terminal_id")
        status = data.get("status")
        board_columns = (worker_id, worker_name, terminal_id, status)
        if not all(isinstance(value, str) and value.strip() for value in board_columns):
            continue
        if status not in ALLOWED_WORKER_STATUSES:
            continue

        current_issue = data.get("current_issue")
        normalized_issue = (
            current_issue if isinstance(current_issue, str) and current_issue.strip() else None
        )
        record_ts = record.get("ts")
        record_ts_dt = _parse_ts(record_ts)
        existing = latest_by_worker.get(worker_id)
        if existing is not None:
            existing_ts_dt = _parse_ts(existing.get("last_update"))
            if existing_ts_dt is not None and (
                record_ts_dt is None or record_ts_dt <= existing_ts_dt
            ):
                continue
        latest_by_worker[worker_id] = {
            "worker_id": worker_id,
            "worker_name": worker_name,
            "terminal_id": terminal_id,
            "current_issue": normalized_issue,
            "current_issue_source": CURRENT_ISSUE_SOURCE,
            "ownership_source": OWNERSHIP_SOURCE,
            "status": status,
            "last_update": record_ts if isinstance(record_ts, str) else None,
        }

    return sorted(
        latest_by_worker.values(),
        key=lambda row: (row["worker_name"].lower(), row["worker_id"].lower()),
    )


def _format_updated(value: Optional[str]) -> str:
    if not value:
        return "-"
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%Y-%m-%d %H:%M")
    except ValueError:
        return value


def format_worker_board(rows: List[Dict[str, Any]]) -> str:
    if not rows:
        return "AI TEAM\n\n(no worker states)"

    rendered_rows = [
        {
            "worker": row["worker_name"],
            "status": row["status"],
            "issue": row["current_issue"] or "-",
            "terminal": row["terminal_id"],
            "updated": _format_updated(row.get("last_update")),
        }
        for row in rows
    ]
    headers = {
        "worker": "worker",
        "status": "status",
        "issue": "issue",
        "terminal": "terminal",
        "updated": "updated",
    }
    widths = {
        key: max(len(headers[key]), max(len(row[key]) for row in rendered_rows)) for key in headers
    }
    column_order = ("worker", "status", "issue", "terminal", "updated")

    lines = ["AI TEAM", ""]
    lines.append("  ".join(headers[key].ljust(widths[key]) for key in column_order))
    lines.append("  ".join("-" * widths[key] for key in column_order))
    for row in rendered_rows:
        lines.append("  ".join(row[key].ljust(widths[key]) for key in column_order))
    lines.extend(
        [
            "",
            "note: issue is a registry hint; claim/handoff ownership lives on GitHub",
        ]
    )
    return "\n".join(lines)
