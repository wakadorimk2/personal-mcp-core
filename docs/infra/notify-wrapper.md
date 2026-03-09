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

### Required setup

1. Add a `notify` entry to `~/.codex/config.toml` with an absolute path to this
   repo's bridge script.
2. Export Discord delivery variables in the shell environment that launches
   Codex.
3. Run a dry-run locally through `scripts/codex_notify.py` before attempting a
   real Discord delivery.

`~/.codex/config.toml` example:

```toml
notify = ["python3", "/absolute/path/to/personal-mcp-core/scripts/codex_notify.py"]
```

Discord delivery environment:

```bash
export NOTIFY_CHANNEL=discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

Optional overrides:

```bash
export DISCORD_WEBHOOK_USERNAME="Codex"
export DISCORD_WEBHOOK_AVATAR_URL="https://example.com/codex.png"
```

Where to configure them:

- Put `notify = [...]` in `~/.codex/config.toml`
- Put `NOTIFY_CHANNEL` and `DISCORD_WEBHOOK_URL` in the shell startup file or
  wrapper script that launches Codex
- If you use WSL, configure them inside the WSL environment where `codex` and
  `python3` actually run; Windows-side env vars are not assumed to propagate
  automatically

Path and shell assumptions:

- The `notify` command uses `python3`, so that executable must exist in the
  environment where Codex runs
- The path in `~/.codex/config.toml` must be an absolute path to
  `scripts/codex_notify.py`; do not rely on the current working directory
- `scripts/codex_notify.py` resolves the repo root from its own file location,
  so calling it through an absolute path is sufficient

Current mapping for Codex task completion:

- `type = "agent-turn-complete"` -> `notify --event task_completed`
- top-level `client` -> `--source` (`codex-tui` など)
- `input-messages` / `input_messages` の末尾 -> `--title`
- `last-assistant-message` -> MESSAGE

The bridge keeps `scripts/notify` as the single notification entrypoint, so
channel selection still comes from `NOTIFY_CHANNEL` / `NOTIFY_CHANNEL_DIR`.

### Dry-run verification

Run the bridge directly before enabling real Discord delivery:

```bash
python3 /absolute/path/to/personal-mcp-core/scripts/codex_notify.py \
  '{"type":"agent-turn-complete","client":"codex-tui","input-messages":["issue #220"],"last-assistant-message":"done"}'
```

Expected result with the default `stdout` channel:

```text
[task_completed/codex-tui] issue #220: done
```

If you want to verify the Discord path without editing `~/.codex/config.toml`
yet, export `NOTIFY_CHANNEL=discord` and `DISCORD_WEBHOOK_URL` in the same
shell, then rerun the command above. A successful Discord webhook send produces
no stdout output and exits with code `0`.

Real Discord smoke-test evidence is tracked separately in issue #268 so this
documented setup can stay reproducible without requiring a live webhook during
issue #267.

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
