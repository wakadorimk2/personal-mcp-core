from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from personal_mcp.core.event import ALLOWED_DOMAINS, build_v1_record
from personal_mcp.storage.events_store import append_event

ALLOWED_KINDS: frozenset = frozenset(
    {"note", "session", "artifact", "milestone", "interaction", "maintenance"}
)
ALLOWED_UI_MODES: frozenset = frozenset({"quick", "tag", "text"})
ALLOWED_UI_EVENT_NAMES: frozenset = frozenset(
    {"ui_mode_changed", "input_started", "input_submitted"}
)
DEFAULT_DOMAIN = "general"
DEFAULT_KIND = "note"


def suggest_labels(text: str) -> Dict[str, str]:
    """Suggest domain/kind labels from free text using lightweight heuristics."""
    normalized = text.lower()

    domain = DEFAULT_DOMAIN
    if any(k in normalized for k in ("poe", "map", "atlas", "ボス", "loot")):
        domain = "poe2"
    elif any(k in normalized for k in ("mood", "疲", "眠", "気分", "しんど")):
        domain = "mood"
    elif any(k in normalized for k in ("todo", "meeting", "進捗", "作業", "タスク")):
        domain = "worklog"
    elif any(k in normalized for k in ("issue", "pr", "実装", "設計", "docs", "コード")):
        domain = "eng"

    kind = DEFAULT_KIND
    if any(k in normalized for k in ("完了", "達成", "release", "マイルストーン")):
        kind = "milestone"
    elif any(k in normalized for k in ("作成", "更新", "artifact", "成果物")):
        kind = "artifact"
    elif any(k in normalized for k in ("調査", "検証", "対応", "実施", "session")):
        kind = "session"

    return {"domain": domain, "kind": kind}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def event_add_sqlite(
    *,
    domain: Optional[str] = None,
    kind: Optional[str] = None,
    text: str = "",
    annotation: Optional[str] = None,
    data_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Build an Event Contract v1 record and append to SQLite.

    domain/kind are optional. If omitted, defaults or label suggestions are used.
    text may be empty. annotation is stored in data.annotation only when non-empty.
    """
    suggested = suggest_labels(text)
    normalized_domain = (domain or "").strip() or suggested["domain"]
    normalized_kind = (kind or "").strip() or suggested["kind"]

    if normalized_domain not in ALLOWED_DOMAINS:
        raise ValueError(f"unsupported domain: {normalized_domain}")
    if normalized_kind not in ALLOWED_KINDS:
        raise ValueError(f"unsupported kind: {normalized_kind}")

    extra: Dict[str, Any] = {}
    if annotation:
        extra["annotation"] = annotation

    record = build_v1_record(
        ts=_now_iso(),
        domain=normalized_domain,
        text=text,
        tags=[],
        kind=normalized_kind,
        source="web-form",
        extra_data=extra or None,
    )
    append_event(record, data_dir=data_dir)
    return record


def ui_event_add_sqlite(
    *,
    event_name: str,
    ui_mode: str,
    data_dir: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Persist UI telemetry for UX experiments using Event Contract v1."""
    normalized_event_name = (event_name or "").strip()
    normalized_ui_mode = (ui_mode or "").strip()

    if normalized_event_name not in ALLOWED_UI_EVENT_NAMES:
        raise ValueError(f"unsupported ui event: {normalized_event_name}")
    if normalized_ui_mode not in ALLOWED_UI_MODES:
        raise ValueError(f"unsupported ui mode: {normalized_ui_mode}")

    payload_data: Dict[str, Any] = {
        "event_name": normalized_event_name,
        "ui_mode": normalized_ui_mode,
    }
    if extra_data:
        payload_data.update(extra_data)

    record = build_v1_record(
        ts=_now_iso(),
        domain=DEFAULT_DOMAIN,
        text=f"[ui] {normalized_event_name}",
        tags=["ux", "experiment"],
        kind="interaction",
        source="web-form-ui",
        extra_data=payload_data,
    )
    append_event(record, data_dir=data_dir)
    return record
