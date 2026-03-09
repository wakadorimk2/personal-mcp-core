from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _infer_role(repo_root: Path) -> str:
    name = repo_root.name.lower()
    if "advisor" in name:
        return "advisor"
    if "builder" in name:
        return "builder"
    if "ops" in name:
        return "ops"
    return "human"


def _default_branch_pattern(role: str | None) -> str:
    if role == "advisor":
        return r"^docs([/-].+)$"
    if role == "builder":
        return r"^(feat|fix)([/-].+)$"
    if role == "ops":
        return r"^ops([/-].+)$"
    return r"^(?!main$).+"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_launch.py",
        description="Guard Codex launches against unexpected worktree/branch context.",
    )
    parser.add_argument("--expect-role", default=os.environ.get("CODEX_EXPECT_ROLE"))
    parser.add_argument("--expect-worktree", default=os.environ.get("CODEX_EXPECT_WORKTREE"))
    parser.add_argument(
        "--expect-branch-pattern",
        default=os.environ.get("CODEX_EXPECT_BRANCH_PATTERN"),
    )
    parser.add_argument(
        "--log-path",
        default=os.environ.get("CODEX_LAUNCH_LOG_PATH"),
        help="JSONL log path. Defaults to ~/.codex/log/codex-launch.jsonl",
    )
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Command to launch. Use -- before the command when passing options.",
    )
    return parser


def _resolve_command(command: list[str]) -> list[str]:
    if command and command[0] == "--":
        command = command[1:]
    return command or ["codex"]


def _log_path(raw_path: str | None) -> Path:
    if raw_path:
        return Path(raw_path).expanduser()
    return Path.home() / ".codex" / "log" / "codex-launch.jsonl"


def _append_log(path: Path, record: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _validate_context(
    cwd: Path,
    repo_root: Path,
    branch: str,
    inferred_role: str,
    expect_role: str | None,
    expect_worktree: str | None,
    expect_branch_pattern: str,
) -> list[str]:
    errors: list[str] = []

    if expect_role and inferred_role != expect_role:
        errors.append(f"role mismatch: expected {expect_role}, got {inferred_role}")

    if expect_worktree:
        expected_root = Path(expect_worktree).expanduser().resolve()
        if repo_root != expected_root:
            errors.append(f"worktree mismatch: expected {expected_root}, got {repo_root}")

    if cwd.resolve() != repo_root:
        errors.append(f"pwd mismatch: expected git top-level {repo_root}, got {cwd.resolve()}")

    if not branch:
        errors.append("branch mismatch: detached HEAD is not allowed")
    elif not re.fullmatch(expect_branch_pattern, branch):
        errors.append(f"branch mismatch: expected /{expect_branch_pattern}/, got {branch}")

    return errors


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        cwd = Path.cwd()
        repo_root = Path(_run_git("rev-parse", "--show-toplevel")).resolve()
        branch = _run_git("branch", "--show-current")
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"codex-launch: failed to inspect git context: {exc}", file=sys.stderr)
        return 2

    inferred_role = _infer_role(repo_root)
    expect_role = args.expect_role
    effective_role = expect_role or inferred_role
    expect_branch_pattern = args.expect_branch_pattern or _default_branch_pattern(effective_role)
    session_id = os.environ.get("CODEX_LAUNCH_SESSION_ID") or str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    record: dict[str, object] = {
        "session_id": session_id,
        "started_at": started_at,
        "cwd": str(cwd.resolve()),
        "worktree_path": str(repo_root),
        "branch": branch,
        "role": inferred_role,
        "expected_role": effective_role,
        "expected_worktree": args.expect_worktree,
        "expected_branch_pattern": expect_branch_pattern,
        "command": _resolve_command(args.command),
    }

    errors = _validate_context(
        cwd=cwd,
        repo_root=repo_root,
        branch=branch,
        inferred_role=inferred_role,
        expect_role=expect_role,
        expect_worktree=args.expect_worktree,
        expect_branch_pattern=expect_branch_pattern,
    )

    log_path = _log_path(args.log_path)
    if errors:
        record["status"] = "blocked"
        record["reason"] = "; ".join(errors)
        _append_log(log_path, record)
        for error in errors:
            print(f"codex-launch: {error}", file=sys.stderr)
        return 2

    record["status"] = "started"
    _append_log(log_path, record)

    command = _resolve_command(args.command)
    try:
        completed = subprocess.run(command, check=False)
    except OSError as exc:
        print(f"codex-launch: failed to launch {' '.join(command)}: {exc}", file=sys.stderr)
        return 127
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
