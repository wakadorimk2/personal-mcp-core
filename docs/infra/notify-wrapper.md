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

## Claude Code integration

`scripts/claude-notify` is a thin wrapper around the `claude` CLI. It forwards
all arguments to `claude "$@"`, then emits a notification through
`scripts/notify`.

Invocation pattern:

```bash
PATH="$PWD/scripts:$PATH"
export NOTIFY_CHANNEL=discord
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."

scripts/claude-notify <claude-args...>
```

Current notification mapping:

- Claude exit `0` -> `task_completed`
- non-zero Claude exit -> `task_failed`
- title -> `Claude Code`
- source -> `claude_code`
- message -> `Claude Code task completed` or `Claude Code exited with status <n>`

Setup requirements:

1. `claude` must be available on `PATH` in the same shell that runs
   `scripts/claude-notify`.
2. `NOTIFY_CHANNEL=discord` and `DISCORD_WEBHOOK_URL` must be exported in that
   same shell, shell startup file, or launcher script.
3. If you use WSL or another wrapper shell, configure the environment where
   `claude`, `curl`, and `python3` actually execute.

Exit semantics:

- `scripts/claude-notify` always exits with the original Claude exit code
- notification delivery failures do not overwrite that exit code
- diagnose delivery problems from stderr, especially the line before
  `claude-notify: notify delivery failed`

### Local verification without a real Discord webhook

These checks validate the current success and failure paths without contacting
Discord. They use a fake `claude` binary and a temporary capture adapter.

Success path:

```bash
tmpdir="$(mktemp -d)"
cat >"$tmpdir/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'claude ok\n'
EOF
chmod +x "$tmpdir/claude"

cat >"$tmpdir/capture" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'event=%s\n' "$NOTIFY_EVENT"
printf 'title=%s\n' "$NOTIFY_TITLE"
printf 'source=%s\n' "$NOTIFY_SOURCE"
printf 'message=%s\n' "$NOTIFY_MESSAGE"
EOF
chmod +x "$tmpdir/capture"

PATH="$tmpdir:$PATH" \
NOTIFY_CHANNEL=capture \
NOTIFY_CHANNEL_DIR="$tmpdir" \
scripts/claude-notify
```

Expected result:

```text
claude ok
event=task_completed
title=Claude Code
source=claude_code
message=Claude Code task completed
```

Failure path:

```bash
cat >"$tmpdir/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'claude failed\n' >&2
exit 17
EOF
chmod +x "$tmpdir/claude"

PATH="$tmpdir:$PATH" \
NOTIFY_CHANNEL=capture \
NOTIFY_CHANNEL_DIR="$tmpdir" \
scripts/claude-notify
echo $?
```

Expected result:

- stdout:

```text
event=task_failed
title=Claude Code
source=claude_code
message=Claude Code exited with status 17
```

- stderr:

```text
claude failed
```

- final exit code: `17`

### Discord delivery troubleshooting

Use the same fake `claude` binary above when you want to test Discord delivery
behavior in isolation. That keeps the check local and distinguishes it from a
real smoke test with a live webhook.

Missing webhook configuration:

```bash
cat >"$tmpdir/claude" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'claude ok\n'
EOF
chmod +x "$tmpdir/claude"

PATH="$tmpdir:$PATH" \
NOTIFY_CHANNEL=discord \
scripts/claude-notify
echo $?
```

Expected result:

- stdout:

```text
claude ok
```

- stderr contains both:

```text
discord notify: DISCORD_WEBHOOK_URL is required
claude-notify: notify delivery failed
```

- final exit code: `0` because Claude itself succeeded

HTTP failure from the webhook endpoint:

```bash
cat >"$tmpdir/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf '500'
EOF
chmod +x "$tmpdir/curl"

PATH="$tmpdir:/usr/bin:/bin" \
NOTIFY_CHANNEL=discord \
DISCORD_WEBHOOK_URL="https://discord.example/webhook" \
scripts/claude-notify
echo $?
```

Expected stderr:

```text
discord notify: webhook POST failed with HTTP 500
claude-notify: notify delivery failed
```

Transport failure from `curl`:

```bash
cat >"$tmpdir/curl" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
printf 'curl: (7) failed to connect\n' >&2
exit 7
EOF
chmod +x "$tmpdir/curl"

PATH="$tmpdir:/usr/bin:/bin" \
NOTIFY_CHANNEL=discord \
DISCORD_WEBHOOK_URL="https://discord.example/webhook" \
scripts/claude-notify
echo $?
```

Expected stderr:

```text
curl: (7) failed to connect
discord notify: webhook POST failed
claude-notify: notify delivery failed
```

Operational checklist:

- If `DISCORD_WEBHOOK_URL is required` appears, export the webhook in the same
  environment that launches `scripts/claude-notify`
- If `webhook POST failed with HTTP ...` appears, verify the webhook URL,
  webhook rotation state, and any proxy or ingress policy between the runner
  and Discord
- If `curl: (...)` appears, treat it as network, DNS, TLS, or local `curl`
  availability trouble first
- If Claude returned a non-zero status, fix that task failure separately from
  notification delivery

Local verification above proves wrapper behavior only. A real Discord smoke
test requires a live webhook and should be recorded separately from this
runbook.

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
