from __future__ import annotations

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


def _git(path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def _seed_origin(origin_path: Path) -> None:
    subprocess.run(["git", "init", "--bare", str(origin_path)], check=True)
    seed_path = origin_path.parent / "seed"
    seed_path.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=seed_path, check=True)
    _git(seed_path, "config", "user.name", "Test User")
    _git(seed_path, "config", "user.email", "test@example.com")
    (seed_path / "README.md").write_text("guard test\n", encoding="utf-8")
    _git(seed_path, "add", "README.md")
    _git(seed_path, "commit", "-m", "init")
    _git(seed_path, "remote", "add", "origin", str(origin_path))
    _git(seed_path, "push", "-u", "origin", "main")
    _git(origin_path, "symbolic-ref", "HEAD", "refs/heads/main")


def _clone_repo(origin_path: Path, clone_path: Path) -> None:
    subprocess.run(["git", "clone", str(origin_path), str(clone_path)], check=True)
    _git(clone_path, "config", "user.name", "Test User")
    _git(clone_path, "config", "user.email", "test@example.com")


def _run_guard(
    repo_path: Path,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    script = _repo_root() / "scripts" / "codex_git_guard.py"
    return subprocess.run(
        ["python3", str(script), *args],
        cwd=repo_path,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def test_codex_git_guard_blocks_on_worktree_mismatch(tmp_path: Path) -> None:
    origin_path = tmp_path / "origin.git"
    _seed_origin(origin_path)
    repo_path = tmp_path / "pmc-ops"
    _clone_repo(origin_path, repo_path)

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(tmp_path / "pmc-builder"),
        "--expect-branch",
        "main",
        "--expect-remote",
        "origin",
        "--",
        "pull",
    )

    assert result.returncode == 2
    assert "worktree mismatch" in result.stderr
    assert "recovery" in result.stderr


def test_codex_git_guard_blocks_on_branch_mismatch(tmp_path: Path) -> None:
    origin_path = tmp_path / "origin.git"
    _seed_origin(origin_path)
    repo_path = tmp_path / "pmc-ops"
    _clone_repo(origin_path, repo_path)
    _git(repo_path, "switch", "-c", "fix/test-guard")

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(repo_path),
        "--expect-branch",
        "main",
        "--expect-remote",
        "origin",
        "--",
        "pull",
    )

    assert result.returncode == 2
    assert "branch mismatch" in result.stderr


def test_codex_git_guard_blocks_on_remote_mismatch(tmp_path: Path) -> None:
    origin_path = tmp_path / "origin.git"
    _seed_origin(origin_path)
    repo_path = tmp_path / "pmc-ops"
    _clone_repo(origin_path, repo_path)
    _git(repo_path, "remote", "add", "fork", str(origin_path))

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(repo_path),
        "--expect-branch",
        "main",
        "--expect-remote",
        "origin",
        "--",
        "pull",
        "fork",
        "main",
    )

    assert result.returncode == 2
    assert "remote mismatch" in result.stderr


def test_codex_git_guard_blocks_on_target_branch_mismatch(tmp_path: Path) -> None:
    origin_path = tmp_path / "origin.git"
    _seed_origin(origin_path)
    repo_path = tmp_path / "pmc-ops"
    _clone_repo(origin_path, repo_path)

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(repo_path),
        "--expect-branch",
        "main",
        "--expect-remote",
        "origin",
        "--",
        "pull",
        "origin",
        "feature",
    )

    assert result.returncode == 2
    assert "target branch mismatch" in result.stderr


def test_codex_git_guard_blocks_on_dirty_tree(tmp_path: Path) -> None:
    origin_path = tmp_path / "origin.git"
    _seed_origin(origin_path)
    repo_path = tmp_path / "pmc-ops"
    _clone_repo(origin_path, repo_path)
    (repo_path / "README.md").write_text("dirty\n", encoding="utf-8")

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(repo_path),
        "--expect-branch",
        "main",
        "--expect-remote",
        "origin",
        "--",
        "pull",
    )

    assert result.returncode == 2
    assert "working tree must be clean" in result.stderr


def test_codex_git_guard_runs_pull_when_context_matches(tmp_path: Path) -> None:
    origin_path = tmp_path / "origin.git"
    _seed_origin(origin_path)
    repo_path = tmp_path / "pmc-ops"
    _clone_repo(origin_path, repo_path)

    result = _run_guard(
        repo_path,
        "--expect-role",
        "ops",
        "--expect-worktree",
        str(repo_path),
        "--expect-branch",
        "main",
        "--expect-remote",
        "origin",
        "--",
        "pull",
        "origin",
        "main",
    )

    assert result.returncode == 0
    assert "Already up to date." in result.stdout
    assert "codex-git-guard:" not in result.stderr
