# notify wrapper

`scripts/notify` is the common entrypoint for CLI tools and local scripts that
need to emit a notification without depending on a specific delivery channel.

## Usage

```bash
PATH="$PWD/scripts:$PATH"
notify "build finished"
notify --event needs_input --title "Codex" "Need approval"
printf 'multiline message' | notify --stdin
```

The default channel is `stdout`, which keeps the initial implementation
cross-platform and CI-safe. The repo also ships `discord` and `discord-test`
adapters for explicit webhook delivery without changing callers.

Discord webhook 向けの最小契約は
[`docs/infra/discord-webhook-channel-contract.md`](./discord-webhook-channel-contract.md)
で別途定義する。

## Notification policy defaults

`scripts/notify` は routing とは別に、通知ごとの policy metadata も正規化する。
現時点で wrapper が adapter へ渡す policy metadata は次の 2 つ。

- `NOTIFY_SEVERITY`: `info` / `warning` / `error`
- `NOTIFY_VERBOSITY`: `debug` / `normal` / `critical`

この policy は現在の v1 では advisory metadata として扱い、wrapper 自体は
suppression や threshold 判定までは行わない。まずは通知の意味と routing に加えて
「人間にどの強度で見せたいか」を adapter 側で参照できる状態を固定する。

Default mapping:

| input | event | severity | verbosity | note |
|---|---|---|---|---|
| `--kind ai_task_completed` | `task_completed` | `info` | `normal` | 通常の完了通知 |
| `--kind ai_task_failed` | `task_failed` | `error` | `critical` | 介入が必要な失敗通知 |
| `--kind smoke_test` | `task_completed` | `info` | `debug` | test webhook 向けの観測通知 |
| `--event needs_input` | `needs_input` | `warning` | `critical` | 人間の入力待ち |
| `--event long_task_finished` | `long_task_finished` | `info` | `normal` | 観測用の終了通知 |
| `--event task_failed` | `task_failed` | `error` | `critical` | kind を通さない失敗通知 |
| other `--event` values | as passed | `info` | `normal` | 既定値 |

`--kind` を使う場合は、その kind に紐づく policy が event 既定値より優先される。
たとえば `--kind smoke_test` は event としては `task_completed` だが、policy は
通常完了通知ではなく `info/debug` として扱う。

## Discord webhook channel

Set `NOTIFY_CHANNEL=discord` or pass `--channel discord`, then provide a
Discord incoming webhook URL through `DISCORD_WEBHOOK_AI_STATUS`.

```bash
export NOTIFY_CHANNEL=discord
export DISCORD_WEBHOOK_AI_STATUS="https://discord.com/api/webhooks/..."
notify --event task_completed --title "issue #238" --source codex-tui "done"
```

Optional overrides:

- `DISCORD_WEBHOOK_USERNAME`
- `DISCORD_WEBHOOK_AVATAR_URL`

The adapter sends plain-text webhook payloads only. Missing webhook
configuration exits with code `2`; HTTP or transport failures exit with code
`1`.

If you need normal Discord delivery split by environment, set
`NOTIFY_ENV=dev` or `NOTIFY_ENV=prod` before calling `notify`. In that case
the logical `discord` route switches to env-specific webhook names:

| `NOTIFY_ENV` | webhook env var | secret-file fallback |
|---|---|---|
| unset | `DISCORD_WEBHOOK_AI_STATUS` | `~/.config/secrets/discord_webhook.env` |
| `dev` | `DISCORD_WEBHOOK_AI_STATUS_DEV` | `~/.config/secrets/discord_webhook_dev.env` |
| `prod` | `DISCORD_WEBHOOK_AI_STATUS_PROD` | `~/.config/secrets/discord_webhook_prod.env` |

This split applies only to the normal `discord` route. Purpose-aware routing
still takes precedence, so `--kind smoke_test` continues to land on
`discord-test` and does not reuse the `dev` / `prod` webhook selection.

### Routing precedence

`scripts/notify` resolves Discord delivery in three stages:

1. decide the logical route from `--kind` when a purpose-specific route exists
2. fall back to the requested logical channel (`discord` / `discord-test`)
3. if the logical route is still `discord`, apply optional `NOTIFY_ENV=dev|prod`
   webhook selection

Current matrix:

| caller input | logical route | webhook selection | notes |
|---|---|---|---|
| `--channel discord` and `NOTIFY_ENV` unset | `discord` | `DISCORD_WEBHOOK_AI_STATUS` | default normal delivery |
| `--channel discord` and `NOTIFY_ENV=dev` | `discord` | `DISCORD_WEBHOOK_AI_STATUS_DEV` | env split for normal delivery |
| `--channel discord` and `NOTIFY_ENV=prod` | `discord` | `DISCORD_WEBHOOK_AI_STATUS_PROD` | env split for normal delivery |
| `--channel discord-test` with any `NOTIFY_ENV` | `discord-test` | `DISCORD_WEBHOOK_AI_STATUS_TEST` | purpose route ignores env split |
| `--kind smoke_test` with any `NOTIFY_ENV` | `discord-test` | `DISCORD_WEBHOOK_AI_STATUS_TEST` | kind routing wins over env split |

This keeps `dev/prod` split as one branch of the normal Discord route, while
test-oriented delivery remains purpose-aware and fail-closed.

### Secret management

Webhook secret は次の優先順位で解決される。

1. route-selected environment variable
2. route-selected secret-file fallback

adapter は route-selected webhook env var が未設定のときだけ fallback file を読む。
そのため、一時的な差し替えや検証では process env を優先できる。

Example:

```bash
mkdir -p ~/.config/secrets
chmod 700 ~/.config/secrets

echo 'export DISCORD_WEBHOOK_AI_STATUS="https://discord.com/api/webhooks/..."' \
  > ~/.config/secrets/discord_webhook.env

chmod 600 ~/.config/secrets/discord_webhook.env
```

Environment-specific example:

```bash
export NOTIFY_ENV=dev
export DISCORD_WEBHOOK_AI_STATUS_DEV="https://discord.com/api/webhooks/..."
notify --event task_completed --title "issue #285" --source codex-tui "routed to dev"
```

## Discord smoke-test channel

Set `NOTIFY_CHANNEL=discord-test` or pass `--channel discord-test`, then
provide a Discord incoming webhook URL through `DISCORD_WEBHOOK_AI_STATUS_TEST`.

```bash
export NOTIFY_CHANNEL=discord-test
export DISCORD_WEBHOOK_AI_STATUS_TEST="https://discord.com/api/webhooks/..."
notify --event task_completed --title "issue #336 smoke" --source codex-tui "done"
```

`discord-test` uses the same payload format and optional overrides as the
`discord` adapter, but it resolves a different webhook and fails closed:

- `DISCORD_WEBHOOK_AI_STATUS_TEST` environment variable
- `~/.config/secrets/discord_test_webhook.env` fallback
- no fallback to `DISCORD_WEBHOOK_AI_STATUS`

Example:

```bash
mkdir -p ~/.config/secrets
chmod 700 ~/.config/secrets

echo 'export DISCORD_WEBHOOK_AI_STATUS_TEST="https://discord.com/api/webhooks/..."' \
  > ~/.config/secrets/discord_test_webhook.env

chmod 600 ~/.config/secrets/discord_test_webhook.env
```

## Claude Code integration

`scripts/claude-notify` is a thin wrapper around the `claude` CLI. It forwards
all arguments to `claude "$@"`, then emits a notification through
`scripts/notify`.

Invocation pattern:

```bash
PATH="$PWD/scripts:$PATH"
export NOTIFY_CHANNEL=discord
export DISCORD_WEBHOOK_AI_STATUS="https://discord.com/api/webhooks/..."

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
2. `NOTIFY_CHANNEL=discord` must be set in that same shell, shell startup
   file, or launcher script. `DISCORD_WEBHOOK_AI_STATUS` は process env または
   `~/.config/secrets/discord_webhook.env` fallback で解決される。
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
discord notify: DISCORD_WEBHOOK_AI_STATUS is required
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
DISCORD_WEBHOOK_AI_STATUS="https://discord.example/webhook" \
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
DISCORD_WEBHOOK_AI_STATUS="https://discord.example/webhook" \
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

- If `DISCORD_WEBHOOK_AI_STATUS is required` appears, export the webhook in the same
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
   Codex. For day-to-day delivery, use `discord` with
   `DISCORD_WEBHOOK_AI_STATUS`. For smoke tests, call
   `scripts/codex_notify.py --smoke-test` and provide
   `DISCORD_WEBHOOK_AI_STATUS_TEST`.
3. Run a dry-run locally through `scripts/codex_notify.py` before attempting a
   real Discord delivery.

`~/.codex/config.toml` example:

```toml
notify = ["python3", "/absolute/path/to/personal-mcp-core/scripts/codex_notify.py"]
```

Discord delivery environment:

```bash
export NOTIFY_CHANNEL=discord
export DISCORD_WEBHOOK_AI_STATUS="https://discord.com/api/webhooks/..."
```

Smoke-test delivery environment:

```bash
export DISCORD_WEBHOOK_AI_STATUS_TEST="https://discord.com/api/webhooks/..."
```

Optional overrides:

```bash
export DISCORD_WEBHOOK_USERNAME="Codex"
export DISCORD_WEBHOOK_AVATAR_URL="https://example.com/codex.png"
```

Where to configure them:

- Put `notify = [...]` in `~/.codex/config.toml`
- Put `NOTIFY_CHANNEL` in the shell startup file or wrapper script that
  launches Codex
- Put `DISCORD_WEBHOOK_AI_STATUS` either in the shell startup / wrapper environment
  or in `~/.config/secrets/discord_webhook.env`
- Put `DISCORD_WEBHOOK_AI_STATUS_TEST` either in the smoke-test shell environment or
  in `~/.config/secrets/discord_test_webhook.env`
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
- `--smoke-test` -> `notify --kind smoke_test`
- top-level `client` -> `--source` (`codex-tui` など)
- `input-messages` / `input_messages` の末尾 -> `--title`
- `last-assistant-message` -> MESSAGE

The bridge keeps `scripts/notify` as the single notification entrypoint, so
channel selection for day-to-day delivery still comes from `NOTIFY_CHANNEL` /
`NOTIFY_CHANNEL_DIR`. If `NOTIFY_ENV=dev|prod` is set and the route stays on
logical `discord`, the wrapper selects `DISCORD_WEBHOOK_AI_STATUS_DEV` or
`DISCORD_WEBHOOK_AI_STATUS_PROD`. `--smoke-test` still uses kind routing and
lands on `discord-test`.

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
yet, export `NOTIFY_CHANNEL=discord` and `DISCORD_WEBHOOK_AI_STATUS` in the same
shell, then rerun the command above. A successful Discord webhook send produces
no stdout output and exits with code `0`.

For smoke tests that must not reach the prod webhook, switch to
`scripts/codex_notify.py --smoke-test` and provide
`DISCORD_WEBHOOK_AI_STATUS_TEST` instead. If that test webhook is missing, the
adapter exits with code `2` and does not fall back to
`DISCORD_WEBHOOK_AI_STATUS`.

Real Discord smoke-test evidence should be recorded in the relevant Issue or PR,
so this documented setup can stay reproducible without keeping live webhook logs
as permanent repo docs.

## Current event coverage and remaining gaps

This section is intentionally limited to the Codex CLI and Claude Code paths
that issue #255 operationalizes. Local scripts can still call `scripts/notify`
directly with any supported `--event`, but that is a separate integration path
from the day-to-day AI CLI flow documented here.

### Current coverage summary

| path | `task_completed` | `task_failed` | `needs_input` | `long_task_finished` |
|---|---|---|---|---|
| Codex CLI via `scripts/codex_notify.py` | supported | not operationalized | not operationalized | not operationalized |
| Claude Code via `scripts/claude-notify` | supported | supported | unsupported | unsupported |

Current behavior behind that table:

- Codex CLI currently uses the `notify` hook payload documented in this repo
  for `agent-turn-complete`, and `scripts/codex_notify.py` maps that flow to
  `task_completed`
- Claude Code currently emits one notification after the wrapped `claude`
  process exits, mapping exit `0` to `task_completed` and non-zero exit to
  `task_failed`
- Neither current AI CLI path projects contract-level optional fields such as
  `task_ref`, `run_url`, or `next_action` into channel adapters

### Remaining gaps outside the completion-oriented flow

| gap | current state | operational impact | follow-up direction |
|---|---|---|---|
| Codex `task_failed` | Not operationalized in the current repo docs/tests. The documented Codex path covers `agent-turn-complete` only. | A Codex run that stops before completion can fail without an out-of-band notification, so operators still need the terminal or host session to notice it. | Add a dedicated Codex failure path only if Codex exposes a stable failure-side notify signal worth standardizing here. |
| Codex or Claude `needs_input` | Unsupported. Current bridges emit only on task completion or process exit. | Approval waits, clarification requests, and other human-blocked pauses remain silent in Discord and other adapters. | Treat this as a separate contract/bridge feature once a stable upstream signal and `next_action` projection are defined. |
| Codex or Claude `long_task_finished` | Unsupported in the AI CLI wrappers. Current flows only classify whole-task completion, not sub-jobs such as watch/build/sync loops finishing. | Operators cannot rely on the current AI CLI wrappers to distinguish “background job finished” from “requested task finished.” | Handle long-running job notifications in a separate wrapper/launcher design rather than stretching the completion path. |
| Non-completion metadata richness | Partial. The contract defines `next_action`, `task_ref`, `run_url`, and `metadata`, but `scripts/notify` currently projects only title/source/message fields to adapters. | Even where `task_failed` exists today, adapters cannot display actionable follow-up detail without wrapper-contract work. | Keep adapters on the current minimal projection for #255 and cut any metadata expansion as a dedicated wrapper follow-up. |

### Scope boundary for closing #255

Issue #255 can close once the currently shipped Codex and Claude completion
paths are operationalized and real Discord smoke-test evidence is recorded in
the relevant Issue or PR. The gaps above should stay explicit follow-up work, not implied
requirements for closing the Epic:

- `needs_input` remains out of scope for #255
- Codex-side failure notifications remain out of scope for #255
- `long_task_finished` for AI CLI wrappers remains out of scope for #255
- Wrapper-contract expansion for `next_action` / `task_ref` / `run_url` /
  `metadata` remains out of scope for #255

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
