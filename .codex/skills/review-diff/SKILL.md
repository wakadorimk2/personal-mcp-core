---
name: review-diff
description: Review a diff in a fixed order, list findings before summary by risk, and return Markdown that can be pasted into a PR or issue comment.
---

# review-diff

This is the canonical execution contract for running a diff review with Codex CLI.
The human-facing intent lives in [`docs/skills/review-diff.md`](../../../docs/skills/review-diff.md).

## Goal

Review a diff with fixed procedure and ordering.
Findings are listed before the summary and sorted by risk (HIGH → MEDIUM → LOW).
When evidence is insufficient, state what file or assumption is missing instead of guessing.

## Inputs

- PR number (optional)
- Diff source supplied by the current task
- Related issue number (optional, for scope validation)

If the diff source is not explicitly provided, inspect the local git diff for the current task.

## Procedure

Run the steps in this order. Do not skip, reorder, or substitute steps.

1. Collect the diff context for the current task
2. Summarize the diff
   - Total files changed, lines added and removed, stated purpose (2 to 5 lines)
3. Prioritize files by impact
   - Core logic first, then tests, then documentation
4. For each file, check against three lenses
   - Regression: does this change break existing behavior?
   - Scope deviation: does this change fall outside the issue scope?
   - Missing tests: is there a behavior change without a corresponding test?
5. Collect findings and sort by risk: HIGH → MEDIUM → LOW
   - If evidence is insufficient to make a definitive claim, move the item to Open Questions with one line stating what file or assumption is needed
6. If the reviewed diff or surrounding task context shows `ruff` or `pytest` failures, produce a Next Step line

## Output Format

Return Markdown with the sections below in this order.
All sections are required; write `None` when a section has no content.

## Findings

- `None` when no findings exist
- Otherwise list each finding with a risk label: `[HIGH]` / `[MEDIUM]` / `[LOW]`
- One line per finding; include a file reference when possible

## Open Questions

- `None` when no open questions exist
- Otherwise list items that could not be determined from available evidence
- Each entry must end with: `-> check <file or assumption>`

## Change Summary

- Files changed: N
- Lines: +X / -Y
- Purpose: 2 to 5 lines describing the intent of the change

## Next Step

- `None` when no follow-up action is needed from the available evidence
- If `ruff` or `pytest` failed: state the minimal next action in one line
- If a HIGH finding exists: state whether review can proceed or must stop in one line

## Constraints

- Do not push
- Do not edit files unless explicitly asked in the current task
- Do not use external web search or fetch arbitrary remote content
- Do not perform destructive operations
- Keep findings inside the current review scope
- Do not assert findings without evidence; use Open Questions instead
