# Architecture

> This document describes the system structure of `personal-mcp-core`.
> For design principles and AI behavior rules, see `AI_GUIDE.md`.
> For Claude Code-specific instructions, see `CLAUDE.md`.

## Overview

```
personal-mcp-core
├── AI_GUIDE.md              ← Source of truth for AI behavior context
└── src/personal_mcp/
    ├── core/
    │   └── guide.py         ← load_ai_guide(): loads AI_GUIDE.md
    ├── adapters/
    │   └── mcp_server.py    ← get_system_context(): MCP-facing interface
    └── server.py            ← CLI entrypoint
```

**Data flow**: `server.py` → `adapters/mcp_server.py` → `core/guide.py` → `AI_GUIDE.md`

## Layer responsibilities

| Layer | Module | Responsibility |
|-------|--------|----------------|
| Entrypoint | `server.py` | CLI entry; wires adapters together |
| Adapter | `adapters/mcp_server.py` | Translates MCP protocol to internal calls |
| Core | `core/guide.py` | Loads and caches the AI guide text |
| Data | `AI_GUIDE.md` | The guide content itself |

## Extension points

### Adding a new adapter

Adapters live in `src/personal_mcp/adapters/`. Each adapter translates between an
external protocol (MCP, HTTP, CLI) and the core functions.

See `docs/adapters.md` for the naming convention and a step-by-step guide.

### Adding MCP tools

When MCP tools are introduced, they go in `src/personal_mcp/tools/`.
Each tool file should expose a single function and a `TOOL_DEFINITION` dict
(following the MCP tool schema).

Document each tool in `docs/tools.md` when that file is created.

### Adding storage / memory

Persistent storage (daily logs, habit data, game state) belongs in
`src/personal_mcp/storage/`. Design the data model in `docs/data-flow.md` first,
then implement.

Data-dir resolution is a CLI concern in `src/personal_mcp/server.py`.
Resolution order is `--data-dir`, `PERSONAL_MCP_DATA_DIR`, then the XDG default.
Tool-layer functions receive a resolved `data_dir` and do not interpret env vars or XDG.

## Skills layer

Skills define how AI agents interact with this repository.
The canonical (AI-agnostic) definitions live in `docs/skills/`;
AI-specific adapters reference them from their own directories.

```
docs/skills/                          ← Canonical skill definitions (AI-agnostic)
├── codex-claude-bridge.md
├── implement-only.md
├── minimal-safe-impl.md
├── research-propose-structured.md
└── review-preflight.md

.claude/skills/                       ← Claude Code adapters
├── minimal-safe-impl/SKILL.md
└── research-propose-structured/SKILL.md

.codex/skills/                        ← Codex adapters
├── codex-claude-bridge/SKILL.md
├── minimal-safe-impl/SKILL.md
├── research-propose-structured/SKILL.md
└── review-preflight/SKILL.md
```

| Kind | Canonical source | Adapter location |
|---|---|---|
| bridge | `docs/skills/codex-claude-bridge.md` | `.codex/skills/codex-claude-bridge/` |
| impl | `docs/skills/implement-only.md` | no Codex adapter; Claude-oriented canonical doc |
| impl | `docs/skills/minimal-safe-impl.md` | `.claude/skills/minimal-safe-impl/`, `.codex/skills/minimal-safe-impl/` |
| research | `docs/skills/research-propose-structured.md` | `.claude/skills/research-propose-structured/`, `.codex/skills/research-propose-structured/` |
| preflight | `docs/skills/review-preflight.md` | `.codex/skills/review-preflight/` |

**Rule**: canonical docs are AI-agnostic. Adapter files contain only tool-specific invocation syntax and constraints.
`review-preflight` is the explicit Codex execution exception: the docs file explains intent, and `.codex/skills/review-preflight/SKILL.md` is the operational source that Codex should run.

---

## Design decisions

### Why AI_GUIDE.md is duplicated

The guide is kept at repo root for human editing and also packaged inside
`src/personal_mcp/` for `importlib.resources` access in installed environments.
This avoids path-resolution fragility in deployed contexts.

Tradeoff: manual sync is required. Accepted because the file changes rarely.

### Why server.py is a placeholder

The real MCP server requires an MCP library dependency (e.g., `mcp` or `fastmcp`).
That dependency has not been added yet to keep the package installable without
external requirements. The placeholder prints context length to verify the load path.

## Event schema

> Defined in `src/personal_mcp/core/event.py`.
> Current status: **schema definition only** — no write logic is implemented here.

### Purpose

All domains (poe2, mood, general, eng, worklog) converge to a single `Event` type so that:

- Storage code (`append_jsonl`) needs no domain-specific branches.
- History can be reconstructed from JSONL files alone, without domain knowledge.
- Future adapters can filter or aggregate events using the common `domain` and `tags` fields.

### Fields

| Field     | Type              | Description                                              |
|-----------|-------------------|----------------------------------------------------------|
| `ts`      | `str`             | ISO 8601 timestamp (UTC recommended)                     |
| `domain`  | `str`             | Source domain — MVP supported: `"poe2"`, `"mood"`, `"general"`, `"eng"`, `"worklog"` |
| `payload` | `Dict[str, Any]`  | Domain-specific data; all values must be JSON-serializable |
| `tags`    | `List[str]`       | Optional labels for filtering; use `[]` if not needed    |

### JSONL example

```python
from dataclasses import asdict
from personal_mcp.core.event import Event

event = Event(
    ts="2026-03-04T11:00:00+00:00",
    domain="eng",
    payload={"text": "JSONL append-only方針を確認", "meta": {"kind": "milestone"}},
    tags=["schema"],
)

asdict(event)
# {
#   "ts": "2026-03-04T11:00:00+00:00",
#   "domain": "eng",
#   "payload": {"text": "JSONL append-only方針を確認", "meta": {"kind": "milestone"}},
#   "tags": ["schema"]
# }
```

`kind` はトップレベルの `payload` に置かず、`payload.meta.kind` に入れる。
`payload.meta` 自体は省略可能（`poe2-watch` による自動記録など）。

`asdict(event)` の結果はそのまま `append_jsonl(path, asdict(event))` に渡せる。
