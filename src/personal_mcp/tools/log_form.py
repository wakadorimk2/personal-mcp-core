from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from personal_mcp.core.event import ALLOWED_DOMAINS, build_v1_record
from personal_mcp.storage.events_store import append_event

ALLOWED_KINDS: frozenset = frozenset(
    {"note", "session", "artifact", "milestone", "interaction", "maintenance"}
)
ALLOWED_UI_MODES: frozenset = frozenset({"quick", "tag", "text", "dashboard"})
ALLOWED_UI_EVENT_NAMES: frozenset = frozenset(
    {
        "ui_mode_changed",
        "input_started",
        "input_submitted",
        "save_success",
        "save_error",
        "refresh_triggered",
    }
)
INPUT_SUBMITTED_SAVE_TYPE_BY_MODE: Dict[str, str] = {
    "quick": "instant",
    "tag": "manual",
    "text": "manual",
}
INPUT_SUBMITTED_TRIGGER_BY_MODE: Dict[str, str] = {
    "quick": "quick_chip",
    "tag": "candidate_tag",
    "text": "text_submit",
}
DEFAULT_DOMAIN = "general"
DEFAULT_KIND = "note"
ALLOWED_INPUT_SUBMITTED_MODES: frozenset = frozenset(INPUT_SUBMITTED_SAVE_TYPE_BY_MODE)


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


def _normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "y", "on"}:
            return True
        if normalized in {"false", "0", "no", "n", "off", ""}:
            return False
    return bool(value)


def _resolve_input_submitted_mode(ui_mode: str, extra_data: Dict[str, Any]) -> str:
    mode = str(extra_data.get("mode") or "").strip()
    if not mode:
        mode = ui_mode
    if mode not in ALLOWED_INPUT_SUBMITTED_MODES:
        raise ValueError(f"unsupported input mode: {mode}")
    return mode


def _input_submitted_contract_payload(ui_mode: str, extra_data: Dict[str, Any]) -> Dict[str, Any]:
    mode = _resolve_input_submitted_mode(ui_mode, extra_data)
    trigger = str(extra_data.get("trigger") or "").strip()
    if not trigger:
        trigger = INPUT_SUBMITTED_TRIGGER_BY_MODE[mode]
    return {
        "mode": mode,
        "save_type": INPUT_SUBMITTED_SAVE_TYPE_BY_MODE[mode],
        "edited_before_submit": _normalize_bool(extra_data.get("edited_before_submit", False)),
        "trigger": trigger,
    }


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
    if normalized_event_name == "input_submitted":
        payload_data.update(_input_submitted_contract_payload(normalized_ui_mode, extra_data or {}))

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
