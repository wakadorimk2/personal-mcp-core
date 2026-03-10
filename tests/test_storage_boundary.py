import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from personal_mcp.server import main
from personal_mcp.tools.daily_summary import generate_daily_summary
from personal_mcp.tools.event import event_add
from personal_mcp.tools.log_form import event_add_sqlite


def _db_count(db_path: Path) -> int:
    with sqlite3.connect(str(db_path)) as conn:
        return int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])


def test_cli_event_add_writes_primary_storage_only(data_dir: Path) -> None:
    event_add(domain="general", text="cli event", data_dir=str(data_dir))

    db_path = data_dir / "events.db"

    assert db_path.exists()
    assert _db_count(db_path) == 1
    assert not (data_dir / "events.jsonl").exists()


def test_event_today_reads_web_input_via_same_storage_boundary(data_dir: Path, capsys) -> None:
    event_add_sqlite(domain="general", kind="note", text="from web", data_dir=str(data_dir))

    main(["event-today", "--data-dir", str(data_dir)])
    captured = capsys.readouterr()
    assert "[general] from web" in captured.out


def test_summary_reads_cli_event_via_same_storage_boundary(data_dir: Path) -> None:
    rec = event_add(domain="worklog", text="from cli", data_dir=str(data_dir))
    target_date = datetime.fromisoformat(rec["ts"]).astimezone(timezone.utc).strftime("%Y-%m-%d")

    summary = generate_daily_summary(target_date, data_dir=str(data_dir))
    assert "from cli" in summary["data"]["text"]
