---
name: review-preflight
description: Run the Codex PR review preflight in a fixed order and report actionable results without pushing or taking destructive actions.
---

# review-preflight

This is the canonical execution contract for running the review preflight with Codex CLI.
The human-facing intent lives in [`docs/skills/review-preflight.md`](../../../docs/skills/review-preflight.md).

## Goal

Run a minimal pre-review safety pass before deeper review work starts.
Check lint, tests, PR diff context, and obvious risky changes in a fixed order so the result can be pasted into a PR comment.

## Inputs

- PR number (optional)
- Base branch (optional, default: current branch upstream or `main`)
- Expected commands: `ruff check .`, `pytest`, `gh pr diff <PR>` when PR number is available

If the PR number is missing, skip `gh pr diff` and use local git diff against the chosen base branch.
If the base branch is missing, prefer the current branch upstream; otherwise use `main`.

## Procedure

Run the checks in this order.

1. Run `ruff check .`
2. Run `pytest`
3. Collect diff context
   - If PR number is provided: run `gh pr diff <PR>`
   - Otherwise: inspect local git diff against the chosen base branch
4. Summarize the diff in 2 to 5 lines
5. Flag obvious risks
   - destructive file operations
   - wide-scope refactors outside the stated review target
   - dependency, CI, or release-impacting changes
   - missing tests for behavior changes

## Output Format

Return Markdown with the sections below in this order.

## Summary

- Overall status: `✅` / `⚠️` / `❌`
- One-line summary

## Checks

- `ruff`: `✅` / `⚠️` / `❌`
- `pytest`: `✅` / `⚠️` / `❌`
- `diff`: `✅` / `⚠️` / `❌`

## Diff Summary

- 2 to 5 short lines

## Risks

- `None` if no obvious risk was found
- Otherwise list each risk in one line

## Fix Candidates

- Minimal, local fixes only
- `None` if no fix is needed before review

## Next Action

- One line stating whether review can proceed

## Constraints

- Do not push
- Do not use external web search or fetch arbitrary remote content
- Do not perform destructive operations
- Do not change files unless explicitly asked in the current task
- Keep recommendations inside the current review scope
