#!/usr/bin/env bash
set -e

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

if [ -f .venv/bin/activate ]; then
  source .venv/bin/activate
fi

exec "$repo_root/scripts/claude-notify" "$@"
