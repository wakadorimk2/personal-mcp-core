from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def resolve_data_dir(explicit: Optional[str] = None) -> str:
    """Resolve data directory from explicit arg, env var, or XDG default."""
    if explicit:
        return explicit
    env = os.environ.get("PERSONAL_MCP_DATA_DIR")
    if env:
        return env
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg) if xdg else Path.home() / ".local" / "share"
    return str(base / "personal-mcp")
