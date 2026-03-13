# orange-garden

*A personal observability garden for events, annotations, and AI interpretation.*

**orange-garden** is a software bonsai.

It is a long-lived personal observability system where life events,
annotations, and interpretations gradually grow over time.

Instead of treating software as something to finish, orange-garden
treats it as something to cultivate — a garden of events, context,
and evolving insight.

The repository was renamed from `personal-mcp-core` to `orange-garden`. Some runtime names still use the existing Python package and CLI identifiers, `personal_mcp` and `personal-mcp`, while the project concept and documentation move under the new name.

## Software Bonsai

A bonsai is shaped slowly. It is not built once and finished.

orange-garden follows the same idea. Life produces small events. Events gain context through annotations. Annotations accumulate into interpretations. Interpretations become visualizations, summaries, and notifications. AI agents are part of that growth process, but they are not the center of it.

The project treats personal data as a long-lived record of observable change:

```text
events
  ↓
annotations
  ↓
interpretations (AI or human)
  ↓
visualization / notifications
```

This is a developer repository for building that foundation carefully, with append-only records, explicit boundaries, and room for future layers to mature.

## What orange-garden does

orange-garden provides a base system for:

- recording personal life and work events
- storing those events in a durable local runtime
- attaching tags, notes, and later annotations
- generating summaries and candidate interpretations
- showing patterns through dashboards and heatmaps
- sending notifications through local or external channels
- tracking AI worker state and coordination
- supporting multi-agent orchestration around a shared event history

Today, the event layer is the most concrete part of the repository. Annotation and interpretation are treated as deliberate next layers rather than being mixed into raw event storage.

## Core Ideas

### 1. Observation before judgment

The base layer stores observable facts, not scores or conclusions. Meaning belongs in higher layers.

### 2. Append-only history

Events are recorded as a growing timeline. Later context should be added alongside earlier facts, not by rewriting them.

### 3. State changes matter more than time slices

The system is designed around "what changed" rather than constant time tracking.

### 4. AI is a layer, not the substrate

AI workers can annotate, interpret, summarize, and notify, but the underlying record should remain useful without any single model or agent runtime.

### 5. Local-first personal observability

The repository assumes personal data should remain understandable and operable in a local environment, with external delivery used only when explicitly configured.

For the detailed design north star, see [docs/design-principles.md](./docs/design-principles.md).

## Architecture Overview

At a high level, orange-garden is organized as a small set of layers:

```text
input surfaces
  CLI / HTTP / scripts / external logs
          |
          v
event tools and adapters
          |
          v
storage boundary
  local DB + recovery formats
          |
          v
higher-level outputs
  summaries / heatmaps / notifications / worker views / AI runtimes
```

Conceptually, the repository already includes:

- event logging and timeline access
- local web input and heatmap-oriented daily logging
- summary generation and candidate extraction
- Discord-capable notification wrappers
- worker status tracking for AI runtime observation
- adapters and scripts that support agent-driven workflows

Implementation details will continue to evolve, but the architectural direction is stable: facts at the base, interpretation above, presentation at the edge.

For technical structure, see [docs/architecture.md](./docs/architecture.md).

## Example Workflow

An example flow looks like this:

```text
1. Event
   "Wrote a design memo for the input flow"

2. Annotation
   tags: ["design", "ux"]
   context: "follow-up to heatmap input friction"

3. Interpretation
   "Most design work happens after small operational notes"

4. Output
   shown in a timeline, daily summary, heatmap, or notification
```

This separation matters:

- events preserve what happened
- annotations preserve added context
- interpretations preserve meaning that may change later

The event contract itself is documented in [docs/event-contract-v1.md](./docs/event-contract-v1.md).

## Repository Structure

The repository is intentionally small and layered:

```text
src/personal_mcp/
  server.py          CLI entrypoint
  adapters/          HTTP and MCP-facing adapters
  tools/             domain tools: events, summaries, workers, ingest
  storage/           storage boundary and persistence helpers
  core/              shared core helpers

docs/                design, architecture, contracts, workflows
scripts/             notification and automation helpers
tests/               focused test suite
data/                development/sample data only
```

Current domains and adjacent capabilities include:

- personal and work event logging
- mood and general note capture
- engineering and worklog records
- heatmap-oriented daily input flows
- AI worker board / status observation
- GitHub ingest and synchronization utilities
- notification delivery through `stdout` or Discord adapters

## Development Workflow

The repository is still developer-first. The current package and CLI names remain:

- Python package: `personal_mcp`
- console script: `personal-mcp`

Minimal setup:

```bash
python -m venv .venv
source .venv/bin/activate
make setup
make lint
make test
```

Typical local run loop:

```bash
export DATA_DIR="$HOME/.local/share/personal-mcp"

make run DATA_DIR="$DATA_DIR" PORT=8080
make log DATA_DIR="$DATA_DIR" TEXT="Wrote a short event"
make today DATA_DIR="$DATA_DIR"
make summary DATA_DIR="$DATA_DIR" DATE="$(date -u +%F)"
```

You can also invoke the CLI directly:

```bash
python -m personal_mcp.server event-add "Wrote a short event" --domain worklog
python -m personal_mcp.server event-list --date "$(date +%F)"
python -m personal_mcp.server worker-status-set \
  --worker-id claude-1 \
  --worker-name Claude-1 \
  --terminal-id tty-1 \
  --current-issue '#324' \
  --status working
python -m personal_mcp.server worker-claim-state \
  --owner wakadorimk2 \
  --repo orange-garden \
  --issue-number 378 \
  --json
python -m personal_mcp.server worker-claim-post \
  --owner wakadorimk2 \
  --repo orange-garden \
  --issue-number 378 \
  --event-type claim \
  --worker-id codex-1 \
  --runtime codex \
  --reason "start claim baseline" \
  --dry-run
```

Notes:

- runtime data should live outside the repository
- `data/` is for development, tests, and samples
- the runtime is local-first; external notification delivery is opt-in

## Useful Documentation

Start here if you want the current source of truth for specific areas:

| Document | Purpose |
|---|---|
| [docs/design-principles.md](./docs/design-principles.md) | Design north star and philosophy |
| [docs/architecture.md](./docs/architecture.md) | Technical architecture overview |
| [docs/event-contract-v1.md](./docs/event-contract-v1.md) | Canonical event schema |
| [docs/data-directory.md](./docs/data-directory.md) | Data directory rules |
| [docs/daily-input-ux-mvp.md](./docs/daily-input-ux-mvp.md) | Heatmap-first daily input direction |
| [docs/worker-domain.md](./docs/worker-domain.md) | AI worker status domain |
| [docs/worker-claim-protocol.md](./docs/worker-claim-protocol.md) | Worker claim の canonical event log protocol |
| [docs/worker-registry-coordination.md](./docs/worker-registry-coordination.md) | Registry と GitHub の orchestration 境界 |
| [docs/infra/notify-wrapper.md](./docs/infra/notify-wrapper.md) | Notification wrapper and channel behavior |
| [docs/domain-extension-policy.md](./docs/domain-extension-policy.md) | Rules for adding new domains |

## Future Directions

orange-garden is moving toward a fuller event -> annotation -> interpretation system.

Likely directions include:

- first-class annotation storage and retrieval
- more explicit interpretation pipelines for AI agents
- richer dashboards and heatmaps for long-term pattern reading
- stronger multi-agent coordination over shared event history
- better ingest from external tools and personal workflows
- tighter but still optional notification and review loops

The aim is not a productivity dashboard in the narrow sense. The aim is a durable personal observability substrate that can grow with a life, a workflow, and a set of agents over years.

## Privacy and License

- Personal activity data is intended to remain local by default.
- External delivery, such as Discord webhooks, is explicit opt-in.
- Aggregate reporting and broader integrations should be treated as optional layers, not assumptions.
- License status is still being finalized. See [LICENSE](./LICENSE).
