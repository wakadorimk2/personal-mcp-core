# Architecture

> This document describes the system structure of `personal-mcp-core`.
> For design principles and AI behavior rules, see `AI_GUIDE.md`.
> For Claude Code-specific instructions, see `CLAUDE.md`.
> For role boundaries and the authoritative role split policy, see [`docs/AI_ROLE_POLICY.md`](./AI_ROLE_POLICY.md).
> This document covers system structure only; role boundaries, operational rules, and notification operations are not in scope here.

## Overview

```
personal-mcp-core
├── AI_GUIDE.md              ← Source of truth for AI behavior context
└── src/personal_mcp/
    ├── core/
    │   └── guide.py         ← load_ai_guide(): loads AI_GUIDE.md
    ├── adapters/
    │   ├── mcp_server.py    ← get_system_context(): MCP-facing interface
    │   └── http_server.py   ← web-serve HTTP adapter (mobile log form)
    ├── tools/               ← one module per domain (event, daily_summary, github_*, …)
    ├── storage/             ← storage boundary: events_store, jsonl, sqlite, path
    └── server.py            ← subcommand CLI entrypoint (personal-mcp)
```

**Data flow**: `server.py` → `tools/*` / `adapters/*` → `storage/*` / `core/guide.py` → `AI_GUIDE.md` / `data/`

## Layer responsibilities

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Entrypoint | `server.py` | Subcommand CLI; parses args and dispatches to tools/adapters |
| Adapter | `adapters/mcp_server.py` | Translates MCP protocol to internal calls |
| Adapter | `adapters/http_server.py` | HTTP server for mobile log form (`web-serve`) |
| Tools | `tools/*.py` | Domain logic: event, daily_summary, github_*, worker, poe2 |
| Storage | `storage/events_store.py` | Storage boundary: runtime read/write against `events.db`, plus explicit recovery rebuild commands for `events.jsonl` |
| Core | `core/guide.py` | Loads and caches the AI guide text |
| Data | `AI_GUIDE.md` | The guide content itself |

Runtime module の import / layering / dependency 制約は
[`docs/import-layering-dependency-constraints.md`](./import-layering-dependency-constraints.md)
で別管理する。enforcement 実装はそちらを正本として follow-up へ接続する。

## Extension points

### Adding a new adapter

Adapters live in `src/personal_mcp/adapters/`. Each adapter translates between an
external protocol (MCP, HTTP, CLI) and the core functions.

See `docs/adapters.md` for the naming convention and a step-by-step guide.

### Adding MCP tools

When MCP tools are introduced, they go in `src/personal_mcp/tools/`.
Each tool file should expose a single function and a `TOOL_DEFINITION` dict
(following the MCP tool schema).

Document each tool in `docs/adapters.md` or a new `docs/tools/<name>.md` file.

### Adding storage / memory

Persistent storage (daily logs, habit data, game state) belongs in
`src/personal_mcp/storage/`. Design the data model against
`docs/event-contract-v1.md` (the authoritative event schema), then implement.

Data-dir resolution is a CLI concern in `src/personal_mcp/server.py`.
Resolution order is `--data-dir`, `PERSONAL_MCP_DATA_DIR`, then the XDG default.
Tool-layer functions receive a resolved `data_dir` and do not interpret env vars or XDG.

### Current external input surfaces

Current runtime input surfaces are split between adapters and tool-driven ingest.

| Surface | Entry point | Layer | Notes |
|---|---|---|---|
| MCP context | `adapters/mcp_server.py` | adapter | MCP-facing interface |
| Mobile log form | `web-serve` -> `adapters/http_server.py` | adapter | HTTP input surface for event capture |
| GitHub manual sync MVP | `github-sync` -> `tools/github_sync.py` | tool | Reads `/users/{username}/events` first page and writes `eng` events |
| GitHub richer ingest | `github-ingest` -> `tools/github_ingest.py` | tool | Same endpoint, richer `data.*` payload per `docs/eng-ingest-impl.md` |
| Local client log watch | `poe2-watch` -> `tools/poe2_client_watcher.py` | tool | Tails a local file and appends events on area transitions |

GitHub integration is currently implemented as tool-layer CLI ingest, not as an
adapter module. The only runtime adapters shipped today are MCP and HTTP.

## Skills layer

Skills define how AI agents interact with this repository.
Most AI-agnostic definitions live in `docs/skills/`, while high-frequency
execution skills for Codex are folded into `docs/CODEX_RUNBOOK.md`.
AI-specific adapters reference the appropriate canonical source.

```
docs/skills/                          ← Standalone canonical skill definitions
├── clarify-request.md
├── codex-claude-bridge.md
├── implement-only.md
├── research-propose-structured.md
└── issue-split.md

docs/CODEX_RUNBOOK.md                 ← Runbook-backed operational skill canon
├── review-diff
├── review-preflight
├── minimal-safe-impl
├── issue-create
└── issue-project-meta

.claude/skills/                       ← Claude Code adapters
├── clarify-request/SKILL.md
├── minimal-safe-impl/SKILL.md
└── research-propose-structured/SKILL.md

.codex/skills/                        ← Codex adapters
├── clarify-request/SKILL.md
├── codex-claude-bridge/SKILL.md
├── minimal-safe-impl/SKILL.md
├── research-propose-structured/SKILL.md
└── review-preflight/SKILL.md
```

| Kind | Canonical source | Adapter location |
|---|---|---|
| clarify | `docs/skills/clarify-request.md` | `.claude/skills/clarify-request/`, `.codex/skills/clarify-request/` |
| bridge | `docs/skills/codex-claude-bridge.md` | `.codex/skills/codex-claude-bridge/` |
| impl | `docs/skills/implement-only.md` | no Codex adapter; Claude-oriented canonical doc |
| impl | `docs/CODEX_RUNBOOK.md` | `.claude/skills/minimal-safe-impl/`, `.codex/skills/minimal-safe-impl/` |
| research | `docs/skills/research-propose-structured.md` | `.claude/skills/research-propose-structured/`, `.codex/skills/research-propose-structured/` |
| review | `docs/CODEX_RUNBOOK.md` | `.codex/skills/review-diff/`, `.codex/skills/review-preflight/`, `.claude/skills/review-preflight/` |
| issue ops | `docs/CODEX_RUNBOOK.md` | `.codex/skills/issue-create/`, `.codex/skills/issue-project-meta/`, `.claude/skills/issue-create/`, `.claude/skills/issue-project-meta/` |

**Rule**: canonical docs stay tool-agnostic where possible. When a skill is
effectively a fixed part of the Codex execution flow, `docs/CODEX_RUNBOOK.md`
acts as the canonical source and adapters keep only invocation syntax and
runtime-specific constraints.

---

## Design decisions

### Why AI_GUIDE.md is duplicated

The guide is kept at repo root for human editing and also packaged inside
`src/personal_mcp/` for `importlib.resources` access in installed environments.
This avoids path-resolution fragility in deployed contexts.

Tradeoff: manual sync is required. Accepted because the file changes rarely.

### Why server.py is the CLI entrypoint

`server.py` exposes a multi-subcommand CLI (via `argparse`) registered as the
`personal-mcp` console script in `pyproject.toml`. Key subcommands include
`event-add`, `event-today`, `event-list`, `web-serve`, `poe2-watch`,
`github-sync`, `github-ingest`, `summary-generate`, and storage-maintenance
commands (`storage-db-to-jsonl`, `storage-jsonl-to-db`).

Running `python -m personal_mcp.server` without a subcommand exits with a usage
error. Always supply a subcommand (or `--help`) when invoking it directly.

## Event schema

> Authoritative spec: **[docs/event-contract-v1.md](./event-contract-v1.md)**.
> Builder: `src/personal_mcp/core/event.py` (`build_v1_record`).
> Issue #100 で writer migration を実施し、v1 record への移行を進めた。

### Purpose

All domains (poe2, mood, general, eng, worklog) converge to a single `Event` type so that:

- Storage boundary code needs no domain-specific branches.
- History can be reconstructed from Event Contract records without domain knowledge.
- Future adapters can filter or aggregate events using the common `domain` and optional `tags` fields.

### v1 record fields

フィールドの正規定義は **[docs/event-contract-v1.md](./event-contract-v1.md)（正典）** を参照。実装上の型対応:

| Field    | Python type       |
|----------|-------------------|
| `v`      | `int`             |
| `ts`     | `str`             |
| `domain` | `str`             |
| `kind`   | `str`             |
| `data`   | `Dict[str, Any]`  |
| `tags`   | `List[str]`       |
| `source` | `str`             |
| `ref`    | `str`             |

`tags` / `source` / `ref` は optional（省略可）。required keys は正典の「Required top-level keys」に従う。

### Event record example

```python
from personal_mcp.core.event import build_v1_record

record = build_v1_record(
    ts="2026-03-04T11:00:00+00:00",
    domain="eng",
    text="DB-only runtime と recovery 境界を確認",
    tags=["schema"],
    kind="milestone",
)
# {
#   "v": 1,
#   "ts": "2026-03-04T11:00:00+00:00",
#   "domain": "eng",
#   "kind": "milestone",
#   "data": {"text": "DB-only runtime と recovery 境界を確認"},
#   "tags": ["schema"]
# }
```

`build_v1_record` の結果は runtime storage と recovery migration の両方で使う正規レコード形状である。
legacy record（`payload` 形式）は recovery path の `read_jsonl` が読み込み時に v1 形状へ正規化する（`storage/jsonl.py:_normalize_event_record`）。
