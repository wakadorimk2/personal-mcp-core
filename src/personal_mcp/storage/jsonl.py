# src/personal_mcp/storage/jsonl.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List


def append_jsonl(path: Path, record: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _normalize_event_record(record: Dict[str, Any]) -> Dict[str, Any]:
    if "payload" in record and "data" not in record:
        payload = record.get("payload")
        payload_dict = payload if isinstance(payload, dict) else {}
        meta = payload_dict.get("meta")
        meta_dict = meta if isinstance(meta, dict) else {}

        normalized = {k: v for k, v in record.items() if k != "payload"}
        data = {k: v for k, v in payload_dict.items() if k != "meta"}

        for key in ("kind", "source", "ref"):
            if key not in normalized and key in meta_dict:
                normalized[key] = meta_dict[key]

        for key, value in meta_dict.items():
            if key not in {"kind", "source", "ref"} and key not in data:
                data[key] = value

        normalized["data"] = data
        return normalized
    return record


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            out.append(_normalize_event_record(json.loads(line)))
    return out
