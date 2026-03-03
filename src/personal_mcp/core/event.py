# src/personal_mcp/core/event.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


ALLOWED_DOMAINS = frozenset({"poe2", "mood", "general", "eng", "worklog"})


@dataclass
class Event:
    """Common event schema for all domains (poe2, mood, general, eng, worklog).

    All fields are JSON-serializable, so dataclasses.asdict(event)
    can be passed directly to append_jsonl without transformation.

    Fields:
        ts:      ISO 8601 timestamp string (UTC recommended)
        domain:  Source domain — MVP supported: "poe2", "mood", "general", "eng", "worklog"
        payload: Domain-specific data; must contain only JSON-serializable values.
                 Conventionally: {"text": ..., "meta": {"kind": ..., "source": ..., "ref": ...}}
                 payload.meta is optional and can be omitted entirely.
        tags:    Labels for filtering; use empty list if not needed
    """

    ts: str
    domain: str
    payload: Dict[str, Any]
    tags: List[str]
