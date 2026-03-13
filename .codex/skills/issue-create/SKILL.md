---
name: issue-create
description: Create a GitHub Issue from issue-draft output, following the canonical spec in docs/CODEX_RUNBOOK.md. Use when Codex should execute gh label list, duplicate check, gh issue create, and record the resulting URL/number. Projects/relationship metadata is handled by issue-project-meta.
---

# issue-create

This file is a thin Codex adapter.

The canonical source of truth for this skill is [`docs/CODEX_RUNBOOK.md`](../../../docs/CODEX_RUNBOOK.md), Appendix D.

Follow the behavior, rules, procedure, and output format defined in that document.

When using this skill, read the canonical doc first and work according to it.

Do not duplicate or redefine the detailed specification here. Update the docs file only when the skill behavior changes.
