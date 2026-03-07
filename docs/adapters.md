# Adapters

Adapters translate between external protocols and `personal_mcp.core` functions.

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
