# notify wrapper

`scripts/notify` is the common entrypoint for CLI tools and local scripts that
need to emit a notification without depending on a specific delivery channel.

## Usage

```bash
PATH="$PWD/scripts:$PATH"
notify "build finished"
notify --event input-required --title "Codex" "Need approval"
printf 'multiline message' | notify --stdin
```

The default channel is `stdout`, which keeps the initial implementation
cross-platform and CI-safe. The repo also ships a `discord` adapter for
explicit opt-in webhook delivery without changing callers.

Discord webhook 向けの最小契約は
[`docs/infra/discord-webhook-channel-contract.md`](./discord-webhook-channel-contract.md)
で別途定義する。

## Discord webhook channel

Set `NOTIFY_CHANNEL=discord` or pass `--channel discord`, then provide a
Discord incoming webhook URL through `DISCORD_WEBHOOK_URL`.

```bash
export NOTIFY_CHANNEL=discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
notify --event task_completed --title "issue #238" --source codex-tui "done"
```

Optional overrides:

- `DISCORD_WEBHOOK_USERNAME`
- `DISCORD_WEBHOOK_AVATAR_URL`

The adapter sends plain-text webhook payloads only. Missing webhook
configuration exits with code `2`; HTTP or transport failures exit with code
`1`.

## Codex CLI integration

Codex CLI's `notify` setting runs an external command and passes one JSON
payload argument. Use `scripts/codex_notify.py` as a thin bridge from that
payload shape into this repo's `scripts/notify` wrapper.

`~/.codex/config.toml` example:

```toml
notify = ["python3", "/absolute/path/to/personal-mcp-core/scripts/codex_notify.py"]
```

Current mapping for Codex task completion:

- `type = "agent-turn-complete"` -> `notify --event task_completed`
- top-level `client` -> `--source` (`codex-tui` など)
- `input-messages` / `input_messages` の末尾 -> `--title`
- `last-assistant-message` -> MESSAGE

The bridge keeps `scripts/notify` as the single notification entrypoint, so
channel selection still comes from `NOTIFY_CHANNEL` / `NOTIFY_CHANNEL_DIR`.

Quick local check:

```bash
python3 scripts/codex_notify.py \
  '{"type":"agent-turn-complete","client":"codex-tui","input-messages":["issue #220"],"last-assistant-message":"done"}'
```

Expected output with the default `stdout` channel:

```text
[task_completed/codex-tui] issue #220: done
```

## Channel contract

- Adapters live under `scripts/notify.d/<channel>` and must be executable.
- The wrapper resolves the channel from `--channel` or `NOTIFY_CHANNEL`.
- The wrapper exports normalized metadata:
  - `NOTIFY_MESSAGE`
  - `NOTIFY_TITLE`
  - `NOTIFY_EVENT`
  - `NOTIFY_SOURCE`
  - `NOTIFY_CHANNEL_NAME`
- The wrapper also sends the message body over stdin.

Using env vars plus stdin keeps the adapter contract stable across bash, WSL,
PowerShell bridges, CI shells, and webhook helpers where positional argument
quoting differs.

The wrapper exits with code `2` for wrapper-side usage/configuration errors.
Adapter-side failures propagate as the adapter's non-zero exit code.

`docs/ai-notification-contract-v1.md` で定義している `task_ref` / `run_url` /
`next_action` / `metadata` は、現時点では channel adapter に投影していない。
v1 の adapter は exported `NOTIFY_*` と stdin だけを入力として扱い、channel
固有の追加 env var を ad-hoc に増やさない。これらを channel 実装で使いたい
場合は、wrapper 契約自体を follow-up で拡張する。

## Adding a channel

1. Add an executable script at `scripts/notify.d/<channel>`.
2. Read notification metadata from the exported `NOTIFY_*` variables.
3. Read stdin when the target tool prefers pipe input over argv.
4. Invoke the platform-specific command from that adapter only.
5. Call the wrapper with `notify --channel <channel> "message"` or set
   `NOTIFY_CHANNEL=<channel>`.

Example skeleton:

```bash
#!/usr/bin/env bash
set -euo pipefail

message="${NOTIFY_MESSAGE:-$(cat)}"
event="${NOTIFY_EVENT:-generic}"

# Call the target notifier here.
printf '[%s] %s\n' "$event" "$message"
```
