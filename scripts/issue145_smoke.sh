#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT_DIR/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT_DIR/.venv/bin/python"
  else
    PYTHON_BIN="python3"
  fi
fi

MODE="check"
RUN_FULL="0"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8080}"
DATA_DIR="${PERSONAL_MCP_DATA_DIR:-/tmp/personal-mcp-145-test}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --serve)
      MODE="serve"
      shift
      ;;
    --full)
      RUN_FULL="1"
      shift
      ;;
    --data-dir)
      DATA_DIR="$2"
      shift 2
      ;;
    --host)
      HOST="$2"
      shift 2
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    *)
      echo "unknown option: $1" >&2
      echo "usage: bash scripts/issue145_smoke.sh [--serve] [--full] [--data-dir DIR] [--host HOST] [--port PORT]" >&2
      exit 2
      ;;
  esac
done

export PERSONAL_MCP_DATA_DIR="$DATA_DIR"

echo "[1/4] ruff"
"$PYTHON_BIN" -m ruff check \
  src/personal_mcp/server.py \
  src/personal_mcp/adapters/http_server.py \
  src/personal_mcp/tools/log_form.py \
  src/personal_mcp/storage/sqlite.py \
  tests/test_log_form.py

echo "[2/4] pytest (targeted)"
"$PYTHON_BIN" -m pytest -q tests/test_log_form.py

if [[ "$RUN_FULL" == "1" ]]; then
  echo "[3/4] pytest (full)"
  "$PYTHON_BIN" -m pytest -q
else
  echo "[3/4] pytest (full) skipped (use --full to enable)"
fi

echo "[4/4] sqlite smoke check"
"$PYTHON_BIN" - <<'PY'
import json
import os
import sqlite3
from pathlib import Path

from personal_mcp.tools.log_form import event_add_sqlite

data_dir = Path(os.environ["PERSONAL_MCP_DATA_DIR"])
data_dir.mkdir(parents=True, exist_ok=True)
event_add_sqlite(domain="general", kind="note", text="smoke")
db_path = data_dir / "events.db"
with sqlite3.connect(str(db_path)) as conn:
    count = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    row = conn.execute("SELECT raw FROM events ORDER BY id DESC LIMIT 1").fetchone()
record = json.loads(row[0])
assert record["domain"] == "general"
assert record["kind"] == "note"
print(f"DB: {db_path}")
print(f"Rows: {count}")
PY

if [[ "$MODE" == "serve" ]]; then
  echo "starting web server: http://$HOST:$PORT"
  exec "$PYTHON_BIN" -m personal_mcp.server web-serve --host "$HOST" --port "$PORT" --data-dir "$DATA_DIR"
fi

echo "done."
echo "manual web test:"
echo "  $PYTHON_BIN -m personal_mcp.server web-serve --host $HOST --port $PORT --data-dir $DATA_DIR"
