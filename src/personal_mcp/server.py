# src/personal_mcp/server.py
from __future__ import annotations

import argparse
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from personal_mcp.adapters.mcp_server import get_system_context
from personal_mcp.tools.event import event_add, event_list
from personal_mcp.tools.poe2_log import log_add, log_list


def _print_event_timeline(records: List[Dict[str, Any]]) -> None:
    """Print events grouped by local date, newest date first.

    Format:
        --- YYYY-MM-DD ---
        HH:MM [domain] text
    """
    def local_date(r: Dict[str, Any]) -> str:
        try:
            return datetime.fromisoformat(r.get("ts", "")).astimezone().strftime("%Y-%m-%d")
        except Exception:
            return "unknown"

    def local_time(r: Dict[str, Any]) -> str:
        try:
            return datetime.fromisoformat(r.get("ts", "")).astimezone().strftime("%H:%M")
        except Exception:
            return "??:??"

    # records are newest-first; preserve that order for date grouping
    seen: List[str] = []
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        d = local_date(r)
        if d not in groups:
            seen.append(d)
            groups[d] = []
        groups[d].append(r)

    for d in seen:
        print(f"--- {d} ---")
        # within each date, display in chronological order (oldest first)
        for r in reversed(groups[d]):
            t = local_time(r)
            dom = r.get("domain", "?")
            text = r.get("payload", {}).get("text", "")
            print(f"{t} [{dom}] {text}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="personal-mcp")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_event = sub.add_parser("event-add", help="append an event to data/events.jsonl")
    p_event.add_argument("text", help="event text")
    p_event.add_argument("--domain", required=True, help="event domain (e.g. poe2, mood)")
    p_event.add_argument("--tags", default="")
    p_event.add_argument("--meta-json", default=None)
    p_event.add_argument("--data-dir", default="data")

    p_elist = sub.add_parser("event-list", help="list events from data/events.jsonl")
    p_elist.add_argument("--n", type=int, default=20)
    p_elist.add_argument("--domain", default=None)
    p_elist.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    p_elist.add_argument("--since", default=None)
    p_elist.add_argument("--data-dir", default="data")
    p_elist.add_argument("--json", action="store_true")

    p_log = sub.add_parser("poe2-log-add", help="append a poe2 log entry")
    p_log.add_argument("text", help="log text")
    p_log.add_argument("--kind", default="note")
    p_log.add_argument("--tags", default="")
    p_log.add_argument("--meta-json", default="{}")
    p_log.add_argument("--data-dir", default="data")

    # src/personal_mcp/server.py の subcommand 追加分だけ（イメージ）
    p_list = sub.add_parser("poe2-log-list", help="list poe2 log entries")
    p_list.add_argument("--n", type=int, default=20)
    p_list.add_argument("--kind", default=None)
    p_list.add_argument("--tag", default=None)
    p_list.add_argument("--since", default=None)
    p_list.add_argument("--data-dir", default="data")
    p_list.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)

    if args.cmd == "event-list":
        records = event_list(
            n=args.n,
            domain=args.domain,
            date=args.date,
            since=args.since,
            data_dir=args.data_dir,
        )
        if args.json:
            print(json.dumps(records, ensure_ascii=False, indent=2))
        else:
            _print_event_timeline(records)
        return 0

    if args.cmd == "event-add":
        tags = [t for t in args.tags.split(",") if t] if args.tags else []
        meta: Optional[Dict[str, Any]] = json.loads(args.meta_json) if args.meta_json else None
        rec = event_add(
            domain=args.domain,
            text=args.text,
            tags=tags,
            meta=meta,
            data_dir=args.data_dir,
        )
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "info":
        text = get_system_context()
        print(f"loaded system context: {len(text)} chars")
        return 0

    if args.cmd == "poe2-log-add":
        tags = [t for t in args.tags.split(",") if t]
        meta: Dict[str, Any] = json.loads(args.meta_json)
        rec = log_add(
            text=args.text,
            kind=args.kind,
            tags=tags,
            meta=meta,
            data_dir=args.data_dir,
        )
        print(json.dumps(rec.__dict__, ensure_ascii=False, indent=2))
        return 0
    
    if args.cmd == "poe2-log-list":
        rows = log_list(
            n=args.n,
            kind=args.kind,
            tag=args.tag,
            since=args.since,
            data_dir=args.data_dir,
        )
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                tags = ",".join(r.get("tags") or [])
                print(f'{r.get("ts","?")} [{r.get("kind","?")}] ({tags}) {r.get("text","")}')
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())