# src/personal_mcp/core/event.py
from __future__ import annotations

from typing import Any, Dict, List, Optional


ALLOWED_DOMAINS = frozenset({"poe2", "mood", "general", "eng", "worklog"})


def build_v1_record(
    *,
    ts: str,
    domain: str,
    text: str,
    tags: List[str],
    kind: Optional[str] = None,
    source: Optional[Any] = None,
    ref: Optional[Any] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a canonical Event Contract v1 record for new writes."""
    data: Dict[str, Any] = {"text": text}
    if extra_data:
        data.update(extra_data)

    record: Dict[str, Any] = {
        "ts": ts,
        "domain": domain,
        "data": data,
        "tags": tags,
        "v": 1,
    }
    if kind is not None:
        record["kind"] = kind
    if source is not None:
        record["source"] = source
    if ref is not None:
        record["ref"] = ref
    return record
