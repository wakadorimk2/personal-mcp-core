# AI CLI Discord smoke log

Issue #268 向けに、Codex CLI と Claude Code の Discord webhook 実送信確認を記録する。
dry-run や fake `curl` ではなく、live webhook を使った実行結果だけを残す。

## 2026-03-10 live webhook verification

This section records the pre-#336 verification run that used the only webhook
path available at that time. After #336, smoke tests should use
`NOTIFY_CHANNEL=discord-test` with `DISCORD_WEBHOOK_AI_STATUS_TEST` so they fail
closed instead of reaching the prod webhook.

### Environment assumptions

- repo root: `/home/wakadori/projects/pmc-ops`
- shell: bash on Linux
- `NOTIFY_CHANNEL=discord`
- webhook secret は process env の `DISCORD_WEBHOOK_AI_STATUS` を優先し、未設定時のみ `~/.config/secrets/discord_webhook.env` fallback を使う
- 成功判定は `scripts/notify.d/discord` の終了条件に従う
  - non-2xx / transport failure は exit `1`
  - config error は exit `2`
  - exit `0` かつ stderr なしなら webhook POST accepted とみなす

### Secret management notes

- repo は local secrets file を必須にしない
- 推奨のローカル管理先は `~/.config/secrets/discord_webhook.env`
- fallback file の想定内容は `export DISCORD_WEBHOOK_AI_STATUS="https://discord.com/api/webhooks/..."`
- 一時的な検証や切り替えでは process env の `DISCORD_WEBHOOK_AI_STATUS` が fallback file より優先される

この「webhook POST accepted」は [`scripts/notify.d/discord`](../../scripts/notify.d/discord)
の実装からの推論であり、Discord channel 上の目視確認まではこの CLI ログだけでは担保しない。

## Codex path

- timestamp: `2026-03-10T08:08:49Z` (`2026-03-10 17:08:49 JST`)
- command:

```bash
NOTIFY_CHANNEL=discord DISCORD_WEBHOOK_AI_STATUS='<configured>' \
python3 scripts/codex_notify.py \
  '{"type":"agent-turn-complete","client":"codex-tui","input-messages":["issue #268 smoke test"],"last-assistant-message":"Codex Discord smoke test completed."}'
```

- observed result:
  - exit code: `0`
  - stdout: empty
  - stderr: empty
  - inferred Discord result: webhook POST accepted

Notes:

- `~/.codex/config.toml` を介した自動 hook ではなく、runbook にある bridge の直接実行で確認した
- 検証対象は `scripts/codex_notify.py` -> `scripts/notify` -> `scripts/notify.d/discord` の delivery path

## Claude path

- timestamp: `2026-03-10T08:08:49Z` (`2026-03-10 17:08:49 JST`)
- command:

```bash
tmpdir="$(mktemp -d)"
cat >"$tmpdir/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'claude smoke ok\n'
exit 0
EOF
chmod +x "$tmpdir/claude"

PATH="$tmpdir:$PATH" \
NOTIFY_CHANNEL=discord \
DISCORD_WEBHOOK_AI_STATUS='<configured>' \
scripts/claude-notify
```

- observed result:
  - exit code: `0`
  - stdout: `claude smoke ok`
  - stderr: empty
  - inferred Discord result: webhook POST accepted

Notes:

- live webhook deliveryだけを切り分けるため、runbook の troubleshooting 手順どおり fake `claude` binary を PATH 先頭に置いた
- 検証対象は `scripts/claude-notify` -> `scripts/notify` -> `scripts/notify.d/discord` の delivery path

## Failure / retry / gap log

- `2026-03-10T08:06:52Z` に 1 回目の試行を実施
  - Codex stderr: `curl: (3) URL using bad/illegal format or missing URL` / `discord notify: webhook POST failed`
  - Claude stderr: `curl: (3) URL using bad/illegal format or missing URL` / `discord notify: webhook POST failed` / `claude-notify: notify delivery failed`
  - cause: shell history から webhook を再構成する際に値の展開を壊した operator-side mistake
  - retry: 元の `export DISCORD_WEBHOOK_AI_STATUS=...` 行を shell でそのまま評価して再実行し、成功
- fallback behavior:
  - process env に `DISCORD_WEBHOOK_AI_STATUS` があればそれを使い、fallback file は読まない
  - process env に `DISCORD_WEBHOOK_AI_STATUS` がなければ `~/.config/secrets/discord_webhook.env` を読む
  - どちらにも値がなければ、adapter は既存どおり設定不足で失敗する
- docs gap:
  - success path は CLI 上で無言 (`exit 0`, stderr なし) のため、HTTP status や Discord message ID は残らない
- 「webhook が accept した」以上の証跡が必要な場合は Discord channel 側の目視確認を別途運用に含める必要がある

## Post-#336 smoke-test path

Use the dedicated test webhook channel for future smoke verification:

```bash
NOTIFY_CHANNEL=discord-test DISCORD_WEBHOOK_AI_STATUS_TEST='<configured>' \
python3 scripts/codex_notify.py \
  '{"type":"agent-turn-complete","client":"codex-tui","input-messages":["issue #336 smoke test"],"last-assistant-message":"Codex Discord test-channel smoke test completed."}'
```

```bash
NOTIFY_CHANNEL=discord-test DISCORD_WEBHOOK_AI_STATUS_TEST='<configured>' \
scripts/notify --event task_completed --title "issue #336 smoke" --source codex-tui "done"
```

Expected behavior:

- the adapter reads `DISCORD_WEBHOOK_AI_STATUS_TEST` or `~/.config/secrets/discord_test_webhook.env`
- if the test webhook is missing, it exits with code `2`
- it does not fall back to `DISCORD_WEBHOOK_AI_STATUS`
- prod Discord webhook should not receive the smoke notification
