from __future__ import annotations

import json
import os
import stat
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / "pyproject.toml").exists():
            return path
        path = path.parent
    raise RuntimeError("pyproject.toml not found; repo root could not be determined")


def _run_codex_notify(
    payload: dict[str, object],
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    script = _repo_root() / "scripts" / "codex_notify.py"
    child_env = dict(os.environ)
    child_env["NOTIFY_CHANNEL"] = "stdout"
    child_env.pop("NOTIFY_CHANNEL_DIR", None)
    if env:
        child_env.update(env)
    return subprocess.run(
        ["python3", str(script), *args, json.dumps(payload)],
        capture_output=True,
        text=True,
        check=True,
        env=child_env,
    )


def test_codex_notify_maps_agent_turn_complete_payload() -> None:
    result = _run_codex_notify(
        {
            "type": "agent-turn-complete",
            "client": "codex-tui",
            "input-messages": ["issue #220 を終わらせて"],
            "last-assistant-message": "PR ready and validation passed.",
        }
    )

    assert (
        result.stdout
        == "[task_completed/codex-tui] issue #220 を終わらせて: PR ready and validation passed.\n"
    )
    assert result.stderr == ""


def test_codex_notify_accepts_legacy_snake_case_input_messages() -> None:
    result = _run_codex_notify(
        {
            "type": "agent-turn-complete",
            "input_messages": ["run the smoke test"],
            "last-assistant-message": "Smoke test completed.",
        }
    )

    assert result.stdout == "[task_completed/codex] run the smoke test: Smoke test completed.\n"
    assert result.stderr == ""


def test_codex_notify_preserves_unknown_payload_type_as_event() -> None:
    result = _run_codex_notify(
        {
            "type": "review_complete",
            "input_messages": ["summarize the diff"],
            "last-assistant-message": "Review completed.",
        }
    )

    assert result.stdout == "[review_complete/codex] summarize the diff: Review completed.\n"
    assert result.stderr == ""


def test_codex_notify_smoke_test_flag_routes_to_discord_test(tmp_path: Path) -> None:
    adapter = tmp_path / "discord"
    adapter.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'channel=%s\\n' \"$NOTIFY_CHANNEL_NAME\"\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'title=%s\\n' \"$NOTIFY_TITLE\"\n"
        "printf 'source=%s\\n' \"$NOTIFY_SOURCE\"\n"
        "printf 'message=%s\\n' \"$NOTIFY_MESSAGE\"\n",
        encoding="utf-8",
    )
    adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)

    result = _run_codex_notify(
        {
            "type": "agent-turn-complete",
            "client": "codex-tui",
            "input_messages": ["issue #371 smoke test"],
            "last-assistant-message": "Codex Discord test-channel smoke test completed.",
        },
        "--smoke-test",
        env={
            "NOTIFY_CHANNEL_DIR": str(tmp_path),
        },
    )

    assert result.stdout.splitlines() == [
        "channel=discord-test",
        "event=task_completed",
        "title=issue #371 smoke test",
        "source=codex-tui",
        "message=Codex Discord test-channel smoke test completed.",
    ]
    assert result.stderr == ""
