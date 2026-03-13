# Adapters

Adapters translate between external protocols and `personal_mcp.core` functions.
Current external input surfaces are not all adapters: some integrations are
implemented as tool-layer CLI entry points instead.

## Naming convention

```
src/personal_mcp/adapters/<name>.py
```

Each adapter file should expose a single public function named `get_<name>_context()`
or similar. Keep adapters thin — no business logic, only protocol translation.

## Current adapters

| Adapter | File | Status |
|---------|------|--------|
| MCP (base) | `adapters/mcp_server.py` | Placeholder |
| HTTP (mobile log form) | `adapters/http_server.py` | MVP (Issue #145) |

These are the only runtime adapters currently shipped.

## Current external input surfaces

| Surface | Entry point | Implementation | Status |
|---|---|---|---|
| MCP context | internal | `adapters/mcp_server.py` | Placeholder |
| HTTP mobile log form | `web-serve` | `adapters/http_server.py` | MVP |
| GitHub manual sync MVP | `github-sync` | `tools/github_sync.py` | Implemented |
| GitHub richer ingest | `github-ingest` | `tools/github_ingest.py` | Implemented |
| Local client log watcher | `poe2-watch` | `tools/poe2_client_watcher.py` | Implemented |

GitHub ingest is intentionally listed here as an external input surface rather
than an adapter. In the current runtime, GitHub is handled by tool-layer CLI
commands that fetch and normalize events before writing through the storage
boundary.

## Adding a new adapter

1. Create `src/personal_mcp/adapters/<name>.py`
2. Implement the interface function (see template below)
3. Add an entry to the table above
4. Wire it into `server.py` if needed

### Template

```python
# src/personal_mcp/adapters/<name>.py
from personal_mcp.core.guide import load_ai_guide


def get_<name>_context() -> str:
    """
    Context payload for <name> integration.
    Extend this function as the adapter grows.
    """
    return load_ai_guide()
```

## Planned adapters

- **poe2**: Path of Exile 2 session context (character state, current goals)
- **daily-log**: Daily log entry template and routing
- **habit**: Habit tracking app integration

These are placeholders. Implement only when the need is concrete.
