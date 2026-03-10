from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    path = Path(__file__).resolve().parent
    while path != path.parent:
        if (path / "pyproject.toml").exists():
            return path
        path = path.parent
    raise RuntimeError("pyproject.toml not found; repo root could not be determined")


def _run_codex_notify(payload: dict[str, object]) -> subprocess.CompletedProcess[str]:
    script = _repo_root() / "scripts" / "codex_notify.py"
    child_env = dict(os.environ)
    child_env["NOTIFY_CHANNEL"] = "stdout"
    child_env.pop("NOTIFY_CHANNEL_DIR", None)
    return subprocess.run(
        ["python3", str(script), json.dumps(payload)],
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
