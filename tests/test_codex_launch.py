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


def _make_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _init_git_repo(path: Path, branch: str = "ops/test-guard") -> None:
    subprocess.run(["git", "init", "-b", branch], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=path, check=True)
    (path / "README.md").write_text("guard test\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True)


def _run_guard(
    repo_path: Path,
    *args: str,
    env: dict[str, str] | None = None,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    script = _repo_root() / "scripts" / "codex_launch.py"
    return subprocess.run(
        ["python3", str(script), *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=check,
        env={**os.environ, **(env or {})},
    )


def test_codex_launch_blocks_on_worktree_mismatch_and_logs_reason(tmp_path: Path) -> None:
    repo_path = tmp_path / "pmc-ops"
    repo_path.mkdir()
    _init_git_repo(repo_path)
    log_path = tmp_path / "codex-launch.jsonl"

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(tmp_path / "pmc-builder"),
        "--log-path",
        str(log_path),
    )

    assert result.returncode == 2
    assert "worktree mismatch" in result.stderr

    records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
    assert records[-1]["status"] == "blocked"
    assert "worktree mismatch" in records[-1]["reason"]
    assert records[-1]["worktree_path"] == str(repo_path.resolve())


def test_codex_launch_blocks_on_main_branch(tmp_path: Path) -> None:
    repo_path = tmp_path / "pmc-ops"
    repo_path.mkdir()
    _init_git_repo(repo_path, branch="main")
    log_path = tmp_path / "codex-launch.jsonl"

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--log-path",
        str(log_path),
    )

    assert result.returncode == 2
    assert "branch mismatch" in result.stderr

    record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert record["status"] == "blocked"
    assert record["branch"] == "main"


def test_codex_launch_runs_command_and_logs_session_context(tmp_path: Path) -> None:
    repo_path = tmp_path / "pmc-ops"
    repo_path.mkdir()
    _init_git_repo(repo_path)
    log_path = tmp_path / "codex-launch.jsonl"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _make_executable(
        bin_dir / "fake-codex",
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'launched\\n'\n",
    )

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(repo_path),
        "--log-path",
        str(log_path),
        "--",
        "fake-codex",
        env={"PATH": f"{bin_dir}:{os.environ['PATH']}"},
    )

    assert result.returncode == 0
    assert result.stdout == "launched\n"
    assert result.stderr == ""

    record = json.loads(log_path.read_text(encoding="utf-8").splitlines()[-1])
    assert record["status"] == "started"
    assert record["branch"] == "ops/test-guard"
    assert record["role"] == "ops"
    assert record["worktree_path"] == str(repo_path.resolve())
    assert record["started_at"]
    assert record["session_id"]
