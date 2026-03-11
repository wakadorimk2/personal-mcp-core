# src/personal_mcp/server.py
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_mcp.adapters.mcp_server import get_system_context
from personal_mcp.storage.events_store import rebuild_db_from_jsonl, rebuild_jsonl_from_db
from personal_mcp.storage.path import resolve_data_dir
from personal_mcp.tools.event import event_add, event_list
from personal_mcp.tools.daily_summary import generate_daily_summary
from personal_mcp.tools.github_sync import github_sync
from personal_mcp.tools.github_ingest import github_ingest
from personal_mcp.tools.poe2_client_watcher import watch_client_log


def _cmd_web_serve(args) -> int:
    from personal_mcp.adapters.http_server import serve

    data_dir = resolve_data_dir(getattr(args, "data_dir", None))
    serve(host=args.host, port=args.port, data_dir=data_dir)
    return 0


def _local_time(r: Dict[str, Any]) -> str:
    try:
        return datetime.fromisoformat(r.get("ts", "")).astimezone().strftime("%H:%M")
    except Exception:
        return "??:??"


def _print_event_lines(records: List[Dict[str, Any]]) -> None:
    """Print events as 'HH:MM [domain] text', oldest first. No headers."""
    for r in reversed(records):  # records are newest-first; display oldest-first
        t = _local_time(r)
        dom = r.get("domain", "?")
        text = r.get("data", {}).get("text", "")
        print(f"{t} [{dom}] {text}")


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
            t = _local_time(r)
            dom = r.get("domain", "?")
            text = r.get("data", {}).get("text", "")
            print(f"{t} [{dom}] {text}")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="personal-mcp")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_event = sub.add_parser("event-add", help="append an event via storage boundary")
    p_event.add_argument("text", help="event text")
    p_event.add_argument("--domain", required=True, help="event domain (e.g. poe2, mood)")
    p_event.add_argument("--tags", default="")
    p_event.add_argument("--meta-json", default=None)
    p_event.add_argument("--data-dir", default=None)

    p_elist = sub.add_parser("event-list", help="list events via storage boundary")
    p_elist.add_argument("--n", type=int, default=20)
    p_elist.add_argument("--domain", default=None)
    p_elist.add_argument("--date", default=None, metavar="YYYY-MM-DD")
    p_elist.add_argument("--since", default=None)
    p_elist.add_argument("--data-dir", default=None)
    p_elist.add_argument("--json", action="store_true")

    p_etoday = sub.add_parser("event-today", help="list today's events")
    p_etoday.add_argument("--domain", default=None)
    p_etoday.add_argument("--data-dir", default=None)
    p_etoday.add_argument("--json", action="store_true")

    p_mood = sub.add_parser("mood-add", help="append a mood event via storage boundary")
    p_mood.add_argument("text", help="mood text")
    p_mood.add_argument("--tags", default="")
    p_mood.add_argument("--data-dir", default=None)

    p_log = sub.add_parser(
        "poe2-log-add", help="append a poe2 log entry"
    )  # legacy: use event-add --domain poe2
    p_log.add_argument("text", help="log text")
    p_log.add_argument("--kind", default="note")
    p_log.add_argument("--tags", default="")
    p_log.add_argument("--meta-json", default="{}")
    p_log.add_argument("--data-dir", default=None)

    p_watch = sub.add_parser("poe2-watch", help="tail Client.txt and record area transitions")
    p_watch.add_argument(
        "--client-log",
        default=None,
        metavar="PATH",
        help="path to Client.txt (overrides POE2_CLIENT_LOG env var)",
    )
    p_watch.add_argument("--data-dir", default=None)

    # src/personal_mcp/server.py の subcommand 追加分だけ（イメージ）
    p_list = sub.add_parser(
        "poe2-log-list", help="list poe2 log entries"
    )  # legacy: use event-list --domain poe2
    p_list.add_argument("--n", type=int, default=20)
    p_list.add_argument("--kind", default=None)
    p_list.add_argument("--tag", default=None)
    p_list.add_argument("--since", default=None)
    p_list.add_argument("--data-dir", default=None)
    p_list.add_argument("--json", action="store_true")

    p_web = sub.add_parser("web-serve", help="start mobile log form HTTP server")
    p_web.add_argument("--host", default="0.0.0.0")
    p_web.add_argument("--port", type=int, default=8080)
    p_web.add_argument("--data-dir", default=None)
    p_ghsync = sub.add_parser("github-sync", help="sync GitHub user events via storage boundary")
    p_ghsync.add_argument("--username", required=True, help="GitHub username")
    p_ghsync.add_argument(
        "--token", default=None, help="GitHub API token (or GITHUB_TOKEN env var)"
    )
    p_ghsync.add_argument("--data-dir", default=None)
    p_ghsync.add_argument("--json", action="store_true")
    p_ghingest = sub.add_parser(
        "github-ingest",
        help="ingest GitHub user events with full data.* payload (eng-ingest-impl.md #247)",
    )
    p_ghingest.add_argument("--username", required=True, help="GitHub username")
    p_ghingest.add_argument(
        "--token", default=None, help="GitHub API token (or GITHUB_TOKEN env var)"
    )
    p_ghingest.add_argument("--data-dir", default=None)
    p_ghingest.add_argument("--json", action="store_true")
    p_summary = sub.add_parser(
        "summary-generate",
        help="generate daily summary for a given UTC date",
    )
    p_summary.add_argument(
        "--date",
        default=None,
        metavar="YYYY-MM-DD",
        help="target date in UTC (default: today UTC)",
    )
    p_summary.add_argument("--annotation", default=None, help="optional annotation text")
    p_summary.add_argument("--interpretation", default=None, help="optional interpretation text")
    p_summary.add_argument("--data-dir", default=None)
    p_summary.add_argument("--json", action="store_true")
    p_db_to_jsonl = sub.add_parser(
        "storage-db-to-jsonl",
        help="recovery-only maintenance: regenerate events.jsonl from events.db",
    )
    p_db_to_jsonl.add_argument("--data-dir", default=None)
    p_db_to_jsonl.add_argument("--dry-run", action="store_true")
    p_db_to_jsonl.add_argument("--json", action="store_true")
    p_jsonl_to_db = sub.add_parser(
        "storage-jsonl-to-db",
        help=(
            "recovery-only maintenance: faithfully reconstruct events.db "
            "from events.jsonl (no dedup applied)"
        ),
    )
    p_jsonl_to_db.add_argument("--data-dir", default=None)
    p_jsonl_to_db.add_argument("--dry-run", action="store_true")
    p_jsonl_to_db.add_argument("--json", action="store_true")

    args = parser.parse_args(argv)
    data_dir = resolve_data_dir(getattr(args, "data_dir", None))

    if args.cmd == "event-today":
        today = datetime.now().astimezone().strftime("%Y-%m-%d")
        records = event_list(
            date=today,
            domain=args.domain,
            data_dir=data_dir,
        )
        if args.json:
            print(json.dumps(records, ensure_ascii=False, indent=2))
        else:
            _print_event_lines(records)
        return 0

    if args.cmd == "event-list":
        records = event_list(
            n=args.n,
            domain=args.domain,
            date=args.date,
            since=args.since,
            data_dir=data_dir,
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
            data_dir=data_dir,
        )
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "info":
        text = get_system_context()
        print(f"loaded system context: {len(text)} chars")
        return 0

    if args.cmd == "mood-add":
        tags = [t for t in args.tags.split(",") if t] if args.tags else []
        rec = event_add(
            domain="mood",
            text=args.text,
            tags=tags,
            data_dir=data_dir,
        )
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "poe2-log-add":
        tags = [t for t in args.tags.split(",") if t]
        meta: Dict[str, Any] = json.loads(args.meta_json)
        rec = event_add(
            domain="poe2",
            text=args.text,
            kind=args.kind,
            tags=tags,
            meta=meta,
            data_dir=data_dir,
        )
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0

    if args.cmd == "web-serve":
        return _cmd_web_serve(args)

    if args.cmd == "poe2-watch":
        client_log = args.client_log or os.environ.get("POE2_CLIENT_LOG")
        if not client_log:
            print("error: --client-log or POE2_CLIENT_LOG must be set", flush=True)
            return 1
        watch_client_log(Path(client_log), data_dir=data_dir)
        return 0

    if args.cmd == "poe2-log-list":
        rows = event_list(
            domain="poe2",
            n=args.n,
            since=args.since,
            data_dir=data_dir,
        )
        if args.kind:
            rows = [r for r in rows if r.get("kind") == args.kind]
        if args.tag:
            rows = [r for r in rows if args.tag in (r.get("tags") or [])]
        if args.json:
            print(json.dumps(rows, ensure_ascii=False, indent=2))
        else:
            for r in rows:
                kind = r.get("kind", "?")
                tags_str = ",".join(r.get("tags") or [])
                text = r.get("data", {}).get("text", "")
                print(f"{r.get('ts', '?')} [{kind}] ({tags_str}) {text}")
        return 0

    if args.cmd == "github-sync":
        token = args.token or os.environ.get("GITHUB_TOKEN")
        result = github_sync(
            username=args.username,
            token=token,
            data_dir=data_dir,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            sv, sk, fl = result["saved"], result["skipped"], result["failed"]
            print(f"saved: {sv}, skipped: {sk}, failed: {fl}")
        return 0

    if args.cmd == "github-ingest":
        token = args.token or os.environ.get("GITHUB_TOKEN")
        result = github_ingest(
            username=args.username,
            token=token,
            data_dir=data_dir,
        )
        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            sv, sk, fl = result["saved"], result["skipped"], result["failed"]
            print(f"saved: {sv}, skipped: {sk}, failed: {fl}")
        return 0

    if args.cmd == "summary-generate":
        target_date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        record = generate_daily_summary(
            target_date,
            annotation=args.annotation,
            interpretation=args.interpretation,
            data_dir=data_dir,
        )
        if args.json:
            print(json.dumps(record, ensure_ascii=False, indent=2))
        else:
            print(f"summary generated for {target_date}: {record['data']['text'][:60]}")
        return 0

    if args.cmd == "storage-db-to-jsonl":
        try:
            result = rebuild_jsonl_from_db(data_dir=data_dir, dry_run=args.dry_run)
        except FileNotFoundError as exc:
            print(f"error: {exc}", flush=True)
            return 1

        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(
                "db->jsonl "
                f"source={result['source_count']} "
                f"target={result['target_count']} "
                f"diff={result['count_diff']} "
                f"dry_run={result['dry_run']}"
            )
        return 0

    if args.cmd == "storage-jsonl-to-db":
        try:
            result = rebuild_db_from_jsonl(data_dir=data_dir, dry_run=args.dry_run)
        except FileNotFoundError as exc:
            print(f"error: {exc}", flush=True)
            return 1

        if args.json:
            print(json.dumps(result, ensure_ascii=False))
        else:
            print(
                "jsonl->db "
                f"source={result['source_count']} "
                f"target={result['target_count']} "
                f"diff={result['count_diff']} "
                f"dry_run={result['dry_run']}"
            )
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
