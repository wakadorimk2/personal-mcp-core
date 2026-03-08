from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("pyproject.toml not found; repo root could not be determined")


def _make_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_wrapper(
    *args: str,
    env: dict[str, str],
    check: bool = True,
) -> subprocess.CompletedProcess:
    script = _repo_root() / "scripts" / "claude-notify"
    return subprocess.run(
        [str(script), *args],
        capture_output=True,
        text=True,
        check=check,
        env={**os.environ, **env},
    )


def test_claude_wrapper_notifies_on_success(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture_dir = tmp_path / "notify.d"
    capture_dir.mkdir()

    _make_executable(
        bin_dir / "claude",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'claude ok\\n'\n",
    )
    _make_executable(
        capture_dir / "capture",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'title=%s\\n' \"$NOTIFY_TITLE\"\n"
        "printf 'source=%s\\n' \"$NOTIFY_SOURCE\"\n"
        "printf 'message=%s\\n' \"$NOTIFY_MESSAGE\"\n",
    )

    result = _run_wrapper(
        "--print",
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "NOTIFY_CHANNEL": "capture",
            "NOTIFY_CHANNEL_DIR": str(capture_dir),
        },
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "claude ok",
        "event=task_completed",
        "title=Claude Code",
        "source=claude_code",
        "message=Claude Code task completed",
    ]
    assert result.stderr == ""


def test_claude_wrapper_notifies_on_failure_and_preserves_exit_code(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture_dir = tmp_path / "notify.d"
    capture_dir.mkdir()

    _make_executable(
        bin_dir / "claude",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'claude failed\\n' >&2\nexit 17\n",
    )
    _make_executable(
        capture_dir / "capture",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'message=%s\\n' \"$NOTIFY_MESSAGE\"\n",
    )

    result = _run_wrapper(
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "NOTIFY_CHANNEL": "capture",
            "NOTIFY_CHANNEL_DIR": str(capture_dir),
        },
        check=False,
    )

    assert result.returncode == 17
    assert result.stdout.splitlines() == [
        "event=task_failed",
        "message=Claude Code exited with status 17",
    ]
    assert result.stderr == "claude failed\n"
