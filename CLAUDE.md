# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This is a personal MCP (Model Context Protocol) context server. Its goal is not to make AI smarter, but to provide stable **assumptions and principles** ("ground")
so that AI misunderstands the owner less. It exposes `AI_GUIDE.md` as a system-level context payload for LLM/tool clients.

## AI workflow: read in this order

When starting any task, read files in this order before writing or changing anything:

1. `CLAUDE.md` (this file) — constraints and conventions
2. `AI_GUIDE.md` — the owner's values and behavioral expectations for AI
3. `docs/AI_ROLE_POLICY.md` — authoritative role split for Claude/Codex operations
4. `docs/architecture.md` — system structure and extension points (if it exists)
5. Only then: the specific files relevant to the task

## AI role split

Claude remains the no-side-effect implementation side, and Codex remains the side-effecting executor/verifier.
Authoritative policy: [`docs/AI_ROLE_POLICY.md`](./docs/AI_ROLE_POLICY.md)

## Practical guardrails for Claude Code

When working in this repo, treat the following as hard constraints:

* Do not create or switch branches
* Do not run commands or report command results as if they were executed
* Do not delete, move, or rewrite files via shell operations; express those changes as unified diff only
* Do not create PRs or prepare GitHub state changes; Codex handles review-ready verification and PR creation

If a deletion is needed, provide:

1. the deleted file path
2. remaining references checked
3. replacement path or rationale for removal
4. verification commands for Codex to run

## Commands

```bash
# Install in editable mode (development)
pip install -e .

# Run the entrypoint (prints loaded context length)
python -m personal_mcp.server

# Verify AI_GUIDE.md copies are in sync
diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md
````

Notes:

* No test runner or linter is configured yet — the repo is intentionally minimal and evolving slowly.

## Architecture

AI_GUIDE.md                          ← Authoritative guide (edit root, then sync copy)
docs/                                ← Design docs referenced from this file
src/personal_mcp/
AI_GUIDE.md                        ← Packaged copy (must match root AI_GUIDE.md)
core/guide.py                      ← load_ai_guide(): loads the guide with two-stage fallback
adapters/mcp_server.py             ← get_system_context(): thin adapter returning the guide text
server.py                          ← CLI entrypoint (placeholder, calls get_system_context)

Data flow: server.py → adapters/mcp_server.py → core/guide.py → AI_GUIDE.md

Event model principle:
* All domains converge to a common event format (timestamp, domain, payload)
* Future auto-ingestion sources follow the same event model — do not diverge
* Design should allow history reconstruction from stored events alone

## Where to put things

| What                                       | Where                                                                        |
| ------------------------------------------ | ---------------------------------------------------------------------------- |
| AI behavior rules (attitude, prohibitions) | AI_GUIDE.md (root), then sync to src/personal_mcp/AI_GUIDE.md                |
| New MCP adapter                            | src/personal_mcp/adapters/<name>.py + entry in docs/adapters.md              |
| New MCP tool                               | src/personal_mcp/tools/<name>.py + entry in docs/tools.md (create if needed) |
| Architecture decisions                     | docs/architecture.md                                                         |
| Bug fix / refactor                         | Relevant .py file only; update docs only if public behavior changes          |
| Claude Code skill definitions              | .claude/skills/<name>/SKILL.md                                               |

## Skills
- Project skills live under `.claude/skills/`.
- For unclear requirements before issue drafting, use: `/clarify-request <request-fragment-or-issue-url>`
- For implementation tasks tied to a GitHub Issue, use: `/minimal-safe-impl <issue-url-or-number>`
- For research/proposal tasks (no code changes), use: `/research-propose-structured <topic-or-issue-url>`

## AI_GUIDE.md sync rule

AI_GUIDE.md exists in two places:

* AI_GUIDE.md (repo root) — human-editable source of truth
* src/personal_mcp/AI_GUIDE.md — packaged copy accessed via importlib.resources

Rule:

* After editing the root file, copy it to the package path and commit both together.
* Verify with: `diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md`

## Branch / commit conventions (minimal)

* Branch names: feat/<topic>, fix/<topic>, docs/<topic>
* Commit messages: imperative, lowercase, no period (e.g., "add poe2 adapter skeleton")
* Keep changes single-concern and reversible

Claude Code note:

* These conventions are for humans or Codex when they perform Git operations
* Claude itself must not create branches, commit, or claim those actions completed

## Key design principle

This repo prioritizes 納得感・安全性・可逆性 (conviction, safety, reversibility) over efficiency and completeness.
Changes should be minimal, reversible, and slow by design. Do not over-engineer or add abstractions ahead of need.

* Do not break the non-evaluative design — avoid scoring, comparative expressions, or implicit improvement suggestions
* Do not add notifications or prompts that encourage user action
* Logs are append-only; treat past records as immutable
* When proposing deletion or overwrite of data, state the irreversibility explicitly and handle with extra care

## Change policy

* Do not make UX more stimulating (no urgency cues, streaks, countdowns, or progress bars)
* Do not introduce gamification elements of any kind
* Do not implement numeric optimization logic ahead of explicit user request

## Compatibility policy

MVP 期間中の互換性方針は以下を参照（重複コピペしない）：

* [README — 互換性ポリシー（MVP期間中）](./README.md#互換性ポリシーmvp期間中)
* [AI_GUIDE.md — 互換性に関するガードレール](./AI_GUIDE.md#互換性に関するガードレール)
* 背景: [Issue #19](https://github.com/wakadorimk2/personal-mcp-core/issues/19)
