from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

PROTECTED_SUBCOMMANDS = {"pull", "merge", "rebase"}
BYPASS_ENV = "PMC_GIT_GUARD_BYPASS"


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_git_guard.py",
        description="Guard pull/merge/rebase against unexpected role/worktree context.",
    )
    parser.add_argument("--expect-role", default=os.environ.get("PMC_GIT_GUARD_EXPECT_ROLE"))
    parser.add_argument(
        "--expect-worktree",
        default=os.environ.get("PMC_GIT_GUARD_EXPECT_WORKTREE"),
        help="Expected git top-level path.",
    )
    parser.add_argument(
        "--expect-branch",
        default=os.environ.get("PMC_GIT_GUARD_EXPECT_BRANCH"),
        help="Expected current branch name before running pull/merge/rebase.",
    )
    parser.add_argument(
        "--expect-remote",
        default=os.environ.get("PMC_GIT_GUARD_EXPECT_REMOTE"),
        help="Expected remote name for git pull.",
    )
    parser.add_argument(
        "git_args",
        nargs=argparse.REMAINDER,
        help="Git arguments to run. Example: pull origin main",
    )
    return parser


def _resolve_git_args(git_args: list[str]) -> list[str]:
    if git_args and git_args[0] == "--":
        git_args = git_args[1:]
    return git_args


def _protected_subcommand(git_args: list[str]) -> str | None:
    if not git_args:
        return None
    subcommand = git_args[0]
    if subcommand in PROTECTED_SUBCOMMANDS:
        return subcommand
    return None


def _is_bypass_enabled() -> bool:
    return os.environ.get(BYPASS_ENV, "").lower() in {"1", "true", "yes", "on"}


def _working_tree_is_clean(repo_root: Path) -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() == ""


def _first_non_option(values: list[str]) -> str | None:
    for value in values:
        if value == "--":
            continue
        if not value.startswith("-"):
            return value
    return None


def _non_option_values(values: list[str]) -> list[str]:
    return [value for value in values if value != "--" and not value.startswith("-")]


def _pull_remote(repo_root: Path, branch: str, git_args: list[str]) -> str | None:
    remote = _first_non_option(git_args[1:])
    if remote:
        return remote
    if not branch:
        return None
    try:
        return _run_git("config", "--get", f"branch.{branch}.remote") or None
    except subprocess.CalledProcessError:
        return None


def _upstream_merge_branch(branch: str) -> str | None:
    if not branch:
        return None
    try:
        merge_ref = _run_git("config", "--get", f"branch.{branch}.merge")
    except subprocess.CalledProcessError:
        return None
    if not merge_ref:
        return None
    return Path(merge_ref).name


def _target_branch(subcommand: str, branch: str, git_args: list[str]) -> str | None:
    positionals = _non_option_values(git_args[1:])
    if subcommand == "pull":
        if len(positionals) >= 2:
            return positionals[1]
        return _upstream_merge_branch(branch)
    if subcommand in {"merge", "rebase"} and positionals:
        return positionals[0]
    return None


def _validate_context(
    repo_root: Path,
    branch: str,
    inferred_role: str,
    subcommand: str,
    git_args: list[str],
    expect_role: str | None,
    expect_worktree: str | None,
    expect_branch: str | None,
    expect_remote: str | None,
) -> list[str]:
    errors: list[str] = []

    if expect_role and inferred_role != expect_role:
        errors.append(f"role mismatch: expected {expect_role}, got {inferred_role}")

    if expect_worktree:
        expected_root = Path(expect_worktree).expanduser().resolve()
        if repo_root != expected_root:
            errors.append(f"worktree mismatch: expected {expected_root}, got {repo_root}")

    if expect_branch and branch != expect_branch:
        actual = branch or "(detached HEAD)"
        errors.append(f"current branch mismatch: expected {expect_branch}, got {actual}")

    if expect_branch:
        actual_target_branch = _target_branch(subcommand, branch, git_args)
        if actual_target_branch and actual_target_branch != expect_branch:
            errors.append(
                f"target branch mismatch: expected {expect_branch}, got {actual_target_branch}"
            )

    if not _working_tree_is_clean(repo_root):
        errors.append(f"working tree must be clean before git {subcommand}")

    if subcommand == "pull" and expect_remote:
        actual_remote = _pull_remote(repo_root, branch, git_args)
        if actual_remote != expect_remote:
            errors.append(
                f"remote mismatch: expected {expect_remote}, got {actual_remote or '(none)'}"
            )

    return errors


def _print_recovery(
    expect_role: str | None,
    expect_worktree: str | None,
    expect_branch: str | None,
) -> None:
    recovery_parts: list[str] = []
    if expect_worktree:
        recovery_parts.append(f"move to {Path(expect_worktree).expanduser().resolve()}")
    elif expect_role:
        recovery_parts.append(f"move to the {expect_role} worktree")
    if expect_branch:
        recovery_parts.append(f"switch to {expect_branch}")

    if recovery_parts:
        print(f"codex-git-guard: recovery: {' and '.join(recovery_parts)}", file=sys.stderr)
    else:
        print(
            "codex-git-guard: recovery: confirm the intended worktree and branch, then retry",
            file=sys.stderr,
        )
    print(
        f"codex-git-guard: bypass: set {BYPASS_ENV}=1 only for intentional one-off overrides",
        file=sys.stderr,
    )


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    git_args = _resolve_git_args(args.git_args)
    if not git_args:
        parser.error("git arguments are required")

    if _is_bypass_enabled():
        return subprocess.run(["git", *git_args], check=False).returncode

    subcommand = _protected_subcommand(git_args)
    if subcommand is None:
        return subprocess.run(["git", *git_args], check=False).returncode

    try:
        repo_root = Path(_run_git("rev-parse", "--show-toplevel")).resolve()
        branch = _run_git("branch", "--show-current")
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"codex-git-guard: failed to inspect git context: {exc}", file=sys.stderr)
        return 2

    inferred_role = _infer_role(repo_root)
    errors = _validate_context(
        repo_root=repo_root,
        branch=branch,
        inferred_role=inferred_role,
        subcommand=subcommand,
        git_args=git_args,
        expect_role=args.expect_role,
        expect_worktree=args.expect_worktree,
        expect_branch=args.expect_branch,
        expect_remote=args.expect_remote,
    )
    if errors:
        for error in errors:
            print(f"codex-git-guard: {error}", file=sys.stderr)
        _print_recovery(args.expect_role, args.expect_worktree, args.expect_branch)
        return 2

    return subprocess.run(["git", *git_args], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
