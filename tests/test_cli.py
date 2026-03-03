# tests/test_cli.py
#
# subprocess.run ベースの integration (E2E) テスト。
# tmp_path を使い本番 data/ を一切汚染しない。
# JSONL ファイルの実体（行数・内容）を直接 assert することで
# 「追記のみ」の性質を E2E レベルで保証する。
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """personal-mcp CLI を同一インタープリタで実行する。"""
    return subprocess.run(
        [sys.executable, "-m", "personal_mcp.server", *args],
        capture_output=True,
        text=True,
        check=check,
    )


# ---------------------------------------------------------------------------
# 1. event-add → event-list の E2E（追記のみ）
# ---------------------------------------------------------------------------


def test_event_add_appends_incrementally(tmp_path: Path) -> None:
    """1回目追加→行数1、2回目追加→行数2、既存行が変わらないことを assert。"""
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    # 1回目
    _run("event-add", "first event", "--domain", "general", "--data-dir", str(data_dir))
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    first_line = lines[0]
    assert json.loads(first_line)["payload"]["text"] == "first event"

    # 2回目
    _run("event-add", "second event", "--domain", "general", "--data-dir", str(data_dir))
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    # 既存行が書き換わっていないことを確認（追記のみ）
    assert lines[0] == first_line
    assert json.loads(lines[1])["payload"]["text"] == "second event"


def test_event_add_event_list_e2e(tmp_path: Path) -> None:
    """event-add で追加したイベントが event-list --json で全件取得できる。"""
    data_dir = tmp_path / "data"

    _run("event-add", "alpha", "--domain", "general", "--data-dir", str(data_dir))
    _run("event-add", "beta", "--domain", "general", "--data-dir", str(data_dir))

    result = _run("event-list", "--json", "--data-dir", str(data_dir))
    records = json.loads(result.stdout)
    assert len(records) == 2
    texts = {r["payload"]["text"] for r in records}
    assert texts == {"alpha", "beta"}


def test_event_add_accepts_eng_domain(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    _run("event-add", "eng event", "--domain", "eng", "--data-dir", str(data_dir))

    record = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["domain"] == "eng"
    assert record["payload"]["text"] == "eng event"


def test_event_add_accepts_worklog_domain(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    _run("event-add", "worklog event", "--domain", "worklog", "--data-dir", str(data_dir))

    record = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["domain"] == "worklog"
    assert record["payload"]["text"] == "worklog event"


def test_event_add_rejects_disallowed_domain_without_creating_file(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    result = _run(
        "event-add",
        "bad event",
        "--domain",
        "art",
        "--data-dir",
        str(data_dir),
        check=False,
    )

    assert result.returncode != 0
    assert not events_path.exists()


# ---------------------------------------------------------------------------
# 2. mood-add → event-list --domain mood
# ---------------------------------------------------------------------------


def test_mood_add_domain_filter(tmp_path: Path) -> None:
    """mood-add → event-list --domain mood で mood イベントのみ返る。"""
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    # general イベントを先に追加
    _run("event-add", "general event", "--domain", "general", "--data-dir", str(data_dir))
    # mood イベントを追加
    _run("mood-add", "少し疲れた", "--data-dir", str(data_dir))

    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2

    # JSONL の domain フィールドを直接検証
    domains = [json.loads(line)["domain"] for line in lines]
    assert "mood" in domains
    assert "general" in domains

    # --domain mood フィルタで mood のみ返る
    result = _run("event-list", "--json", "--domain", "mood", "--data-dir", str(data_dir))
    records = json.loads(result.stdout)
    assert len(records) == 1
    assert records[0]["domain"] == "mood"
    assert records[0]["payload"]["text"] == "少し疲れた"


def test_mood_add_append_only(tmp_path: Path) -> None:
    """mood-add を2回呼んでも既存行が変わらない（追記のみ）。"""
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    _run("mood-add", "1回目", "--data-dir", str(data_dir))
    first_line = events_path.read_text(encoding="utf-8").splitlines()[0]

    _run("mood-add", "2回目", "--data-dir", str(data_dir))
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line


# ---------------------------------------------------------------------------
# 3. poe2-log-add → data/events.jsonl への追記
#    (data/poe2/logs.jsonl は廃止済みのため events.jsonl のみを検証)
# ---------------------------------------------------------------------------


def test_poe2_log_add_appends_to_events_jsonl(tmp_path: Path) -> None:
    """poe2-log-add が events.jsonl に追記されることを E2E で確認。"""
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    # 1回目
    _run("poe2-log-add", "farming T17 map", "--kind", "session", "--data-dir", str(data_dir))
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    first_line = lines[0]
    record = json.loads(first_line)
    assert record["domain"] == "poe2"
    assert record["payload"]["text"] == "farming T17 map"

    # 2回目（追記のみ）
    _run("poe2-log-add", "boss defeated", "--data-dir", str(data_dir))
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    # 既存行が書き換わっていないことを確認
    assert lines[0] == first_line
    assert json.loads(lines[1])["payload"]["text"] == "boss defeated"


def test_poe2_log_add_domain_is_poe2(tmp_path: Path) -> None:
    """poe2-log-add が events.jsonl に domain=poe2 で書くことを確認。"""
    data_dir = tmp_path / "data"
    events_path = data_dir / "events.jsonl"

    _run("poe2-log-add", "note text", "--kind", "note", "--data-dir", str(data_dir))

    record = json.loads(events_path.read_text(encoding="utf-8").splitlines()[0])
    assert record["domain"] == "poe2"
    assert record["payload"]["meta"]["kind"] == "note"
