#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


class NotificationKind:
    AI_TASK_COMPLETED = "ai_task_completed"
    AI_TASK_FAILED = "ai_task_failed"


_RAW_TYPE_TO_KIND: dict[str, str] = {
    "agent-turn-complete": NotificationKind.AI_TASK_COMPLETED,
}


def _repo_root() -> Path:
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / "pyproject.toml").exists():
            return path
        path = path.parent
    raise RuntimeError("pyproject.toml not found; repo root could not be determined")


def _payload_list(payload: dict[str, object], *keys: str) -> list[str]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
    return []


def _payload_text(payload: dict[str, object], *keys: str) -> str:
    for key in keys:
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return ""


def _single_line(text: str, limit: int = 80) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 3].rstrip()}..."


def _notify_args(payload: dict[str, object]) -> list[str]:
    raw_type = _payload_text(payload, "type") or "agent-turn-complete"
    kind = _RAW_TYPE_TO_KIND.get(raw_type)
    source = _payload_text(payload, "client") or "codex"
    input_messages = _payload_list(payload, "input-messages", "input_messages")
    title = _single_line(input_messages[-1]) if input_messages else "Codex task completed"
    message = _payload_text(payload, "last-assistant-message", "last_assistant_message")
    if not message:
        message = "Codex finished the requested task."

    notify = _repo_root() / "scripts" / "notify"
    event_args = ["--kind", kind] if kind is not None else ["--event", raw_type]
    return [str(notify), *event_args, "--title", title, "--source", source, message]


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: codex_notify.py '<codex notify json payload>'", file=sys.stderr)
        return 2

    try:
        payload = json.loads(sys.argv[1])
    except json.JSONDecodeError as exc:
        print(f"codex_notify.py: invalid JSON payload: {exc}", file=sys.stderr)
        return 2

    if not isinstance(payload, dict):
        print("codex_notify.py: payload must be a JSON object", file=sys.stderr)
        return 2

    result = subprocess.run(_notify_args(payload), check=False)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
