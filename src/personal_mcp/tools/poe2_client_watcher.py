# src/personal_mcp/tools/poe2_client_watcher.py
from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Optional

from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.tools.event import event_add

_SCENE_RE = re.compile(r"\[SCENE\] Set Source \[([^\]]+)\]")

# PoE2 emits these literals during area loading transitions (not real area names).
_NOISE_AREAS: frozenset[str] = frozenset({"(null)", "(unknown)"})


def parse_area_line(line: str) -> Optional[str]:
    """Extract area name from a Client.txt [SCENE] line.

    Returns the area name string if the line matches and is not a transient
    loading state, otherwise None.
    """
    m = _SCENE_RE.search(line)
    if not m:
        return None
    area = m.group(1)
    return None if area in _NOISE_AREAS else area


def watch_client_log(
    path: Path,
    data_dir: Optional[str] = None,
    poll_interval: float = 0.2,
) -> None:
    """Tail Client.txt from the current end and emit poe2 events on area transitions.

    Raises KeyboardInterrupt passthrough on Ctrl+C.
    Does NOT replay past lines — seeks to EOF before starting.
    """
    data_dir = resolve_data_dir(data_dir)
    with open(path, encoding="utf-8", errors="replace") as f:
        print(f"poe2-watch: monitoring {path}")
        f.seek(0, os.SEEK_END)
        try:
            while True:
                line = f.readline()
                if not line:
                    time.sleep(poll_interval)
                    continue
                area = parse_area_line(line)
                if area is not None:
                    event_add(
                        domain="poe2",
                        text=area,
                        kind="area_transition",
                        tags=["auto"],
                        meta={
                            "source": "client_txt",
                            "raw": line.rstrip("\n"),
                        },
                        data_dir=data_dir,
                    )
                    print(f"poe2-watch: area_transition -> {area}")
        except KeyboardInterrupt:
            pass
    print("poe2-watch: stopped")
