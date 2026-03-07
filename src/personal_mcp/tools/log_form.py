from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from personal_mcp.core.event import ALLOWED_DOMAINS, build_v1_record
from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.storage.sqlite import append_sqlite

ALLOWED_KINDS: frozenset = frozenset(
    {"note", "session", "artifact", "milestone", "interaction", "maintenance"}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def event_add_sqlite(
    *,
    domain: str,
    kind: str,
    text: str = "",
    annotation: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an Event Contract v1 record and append to SQLite.

    domain and kind are required. text may be empty. annotation is stored in
    data.annotation only when non-empty.
    """
    if domain not in ALLOWED_DOMAINS:
        raise ValueError(f"unsupported domain: {domain}")
    if kind not in ALLOWED_KINDS:
        raise ValueError(f"unsupported kind: {kind}")

    extra: Dict[str, Any] = {}
    if annotation:
        extra["annotation"] = annotation

    record = build_v1_record(
        ts=_now_iso(),
        domain=domain,
        text=text,
        tags=[],
        kind=kind,
        source="web-form",
        extra_data=extra or None,
    )
    db_path = Path(resolve_data_dir(data_dir)) / "events.db"
    append_sqlite(db_path, record)
    return record
