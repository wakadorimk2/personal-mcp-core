# tests/test_cli.py
#
# subprocess.run ベースの integration (E2E) テスト。
# tmp_path を使い本番 data/ を一切汚染しない。
# JSONL ファイルの実体（行数・内容）を直接 assert することで
# 「追記のみ」の性質を E2E レベルで保証する。
from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path


def _run(*args: str, check: bool = True, env: dict | None = None) -> subprocess.CompletedProcess:
    """personal-mcp CLI を同一インタープリタで実行する。"""
    return subprocess.run(
        [sys.executable, "-m", "personal_mcp.server", *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def _repo_root() -> Path:
    """pyproject.toml の位置を起点に repo ルートを特定する。CWD 依存しない。"""
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("pyproject.toml not found; repo root could not be determined")


def _repo_data_jsonl_snapshot() -> dict[Path, str]:
    """repo/data 配下の runtime storage ファイル集合と内容を取得する。"""
    repo_data_dir = _repo_root() / "data"
    if not repo_data_dir.exists():
        return {}
    snapshots: dict[Path, str] = {}
    for pattern in ("*.jsonl", "*.db"):
        for path in repo_data_dir.rglob(pattern):
            snapshots[path] = path.read_bytes().hex()
    return snapshots


def _read_runtime_events(data_dir: Path) -> list[dict]:
    db_path = data_dir / "events.db"
    if not db_path.exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        rows = conn.execute("SELECT raw FROM events ORDER BY id ASC")
        return [json.loads(raw) for (raw,) in rows]


# ---------------------------------------------------------------------------
# 1. event-add → event-list の E2E（追記のみ）
# ---------------------------------------------------------------------------


def test_event_add_appends_incrementally(tmp_path: Path) -> None:
    """1回目追加→行数1、2回目追加→行数2、既存行が変わらないことを assert。"""
    data_dir = tmp_path / "data"

    # 1回目
    _run("event-add", "first event", "--domain", "general", "--data-dir", str(data_dir))
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    first_row = rows[0]
    assert first_row["data"]["text"] == "first event"

    # 2回目
    _run("event-add", "second event", "--domain", "general", "--data-dir", str(data_dir))
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    assert rows[0] == first_row
    assert rows[1]["data"]["text"] == "second event"


def test_event_add_event_list_e2e(tmp_path: Path) -> None:
    """event-add で追加したイベントが event-list --json で全件取得できる。"""
    data_dir = tmp_path / "data"

    _run("event-add", "alpha", "--domain", "general", "--data-dir", str(data_dir))
    _run("event-add", "beta", "--domain", "general", "--data-dir", str(data_dir))

    result = _run("event-list", "--json", "--data-dir", str(data_dir))
    records = json.loads(result.stdout)
    assert len(records) == 2
    texts = {r["data"]["text"] for r in records}
    assert texts == {"alpha", "beta"}


def test_event_add_accepts_eng_domain(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    _run("event-add", "eng event", "--domain", "eng", "--data-dir", str(data_dir))

    record = _read_runtime_events(data_dir)[0]
    assert record["domain"] == "eng"
    assert record["data"]["text"] == "eng event"


def test_event_add_accepts_worklog_domain(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    _run("event-add", "worklog event", "--domain", "worklog", "--data-dir", str(data_dir))

    record = _read_runtime_events(data_dir)[0]
    assert record["domain"] == "worklog"
    assert record["data"]["text"] == "worklog event"


def test_event_add_accepts_summary_domain(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    _run("event-add", "daily summary", "--domain", "summary", "--data-dir", str(data_dir))

    record = _read_runtime_events(data_dir)[0]
    assert record["domain"] == "summary"
    assert record["data"]["text"] == "daily summary"


def test_event_add_rejects_disallowed_domain_without_creating_file(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

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
    assert not (data_dir / "events.db").exists()
    assert not (data_dir / "events.jsonl").exists()


def test_env_var_data_dir_is_used(tmp_path: Path) -> None:
    """PERSONAL_MCP_DATA_DIR のみ指定した場合、その dir に書かれることを E2E で検証。"""
    env_dir = tmp_path / "env_data"
    before = _repo_data_jsonl_snapshot()

    _run(
        "event-add",
        "env test",
        "--domain",
        "general",
        env={**os.environ, "PERSONAL_MCP_DATA_DIR": str(env_dir)},
    )

    rows = _read_runtime_events(env_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["data"]["text"] == "env test"
    assert record["domain"] == "general"
    assert _repo_data_jsonl_snapshot() == before


def test_explicit_data_dir_overrides_env_var(tmp_path: Path) -> None:
    """--data-dir が PERSONAL_MCP_DATA_DIR より優先されることを E2E で検証。
    - explicit_dir に書かれる
    - env_dir には書かれない
    """
    env_dir = tmp_path / "env_data"
    explicit_dir = tmp_path / "explicit_data"
    before = _repo_data_jsonl_snapshot()

    _run(
        "event-add",
        "explicit test",
        "--domain",
        "general",
        "--data-dir",
        str(explicit_dir),
        env={**os.environ, "PERSONAL_MCP_DATA_DIR": str(env_dir)},
    )

    rows = _read_runtime_events(explicit_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["data"]["text"] == "explicit test"
    assert not (env_dir / "events.db").exists()
    assert _repo_data_jsonl_snapshot() == before


# ---------------------------------------------------------------------------
# 4. repo内 data/ に書き込まないことの明示的検証
# ---------------------------------------------------------------------------


def test_writes_to_tmp_not_repo_data_dir(tmp_path: Path) -> None:
    """CLI が tmp_path 側の runtime storage に書き、repo内 data/ には書かないことを明示的に assert。

    - CWD 依存にせず、pyproject.toml 起点で repo root を特定する。
    - テスト前後で repo_root/data 配下の storage ファイルスナップショットを比較する。
    """
    data_dir = tmp_path / "data"

    before = _repo_data_jsonl_snapshot()

    _run("event-add", "repo isolation test", "--domain", "general", "--data-dir", str(data_dir))

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    record = rows[0]
    assert record["data"]["text"] == "repo isolation test"

    # repo/data/ 側の storage ファイルに変化がない
    assert _repo_data_jsonl_snapshot() == before


# ---------------------------------------------------------------------------
# 2. mood-add → event-list --domain mood
# ---------------------------------------------------------------------------


def test_mood_add_domain_filter(tmp_path: Path) -> None:
    """mood-add → event-list --domain mood で mood イベントのみ返る。"""
    data_dir = tmp_path / "data"

    # general イベントを先に追加
    _run("event-add", "general event", "--domain", "general", "--data-dir", str(data_dir))
    # mood イベントを追加
    _run("mood-add", "少し疲れた", "--data-dir", str(data_dir))

    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    domains = [row["domain"] for row in rows]
    assert "mood" in domains
    assert "general" in domains

    # --domain mood フィルタで mood のみ返る
    result = _run("event-list", "--json", "--domain", "mood", "--data-dir", str(data_dir))
    records = json.loads(result.stdout)
    assert len(records) == 1
    assert records[0]["domain"] == "mood"
    assert records[0]["data"]["text"] == "少し疲れた"


def test_mood_add_append_only(tmp_path: Path) -> None:
    """mood-add を2回呼んでも既存行が変わらない（追記のみ）。"""
    data_dir = tmp_path / "data"

    _run("mood-add", "1回目", "--data-dir", str(data_dir))
    first_row = _read_runtime_events(data_dir)[0]

    _run("mood-add", "2回目", "--data-dir", str(data_dir))
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    assert rows[0] == first_row


# ---------------------------------------------------------------------------
# 3. poe2-log-add → events.db への追記
#    (runtime storage は events.db に統一)
# ---------------------------------------------------------------------------


def test_poe2_log_add_appends_to_events_db(tmp_path: Path) -> None:
    """poe2-log-add が events.db に追記されることを E2E で確認。"""
    data_dir = tmp_path / "data"

    # 1回目
    _run("poe2-log-add", "farming T17 map", "--kind", "session", "--data-dir", str(data_dir))
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 1
    first_row = rows[0]
    record = first_row
    assert record["domain"] == "poe2"
    assert record["data"]["text"] == "farming T17 map"

    # 2回目（追記のみ）
    _run("poe2-log-add", "boss defeated", "--data-dir", str(data_dir))
    rows = _read_runtime_events(data_dir)
    assert len(rows) == 2
    assert rows[0] == first_row
    assert rows[1]["data"]["text"] == "boss defeated"


def test_poe2_log_add_domain_is_poe2(tmp_path: Path) -> None:
    """poe2-log-add が events.db に domain=poe2 で書くことを確認。"""
    data_dir = tmp_path / "data"

    _run("poe2-log-add", "note text", "--kind", "note", "--data-dir", str(data_dir))

    record = _read_runtime_events(data_dir)[0]
    assert record["domain"] == "poe2"
    assert record["kind"] == "note"
