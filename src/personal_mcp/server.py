# src/personal_mcp/server.py
from __future__ import annotations

import argparse
import json
from typing import Any, Dict, List, Optional

from personal_mcp.adapters.mcp_server import get_system_context
from personal_mcp.tools.poe2_log import log_add, log_list


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="personal-mcp")
    sub = parser.add_subparsers(dest="cmd", required=True)

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