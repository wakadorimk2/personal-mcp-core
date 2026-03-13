from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    p = Path(__file__).resolve().parent
    while p != p.parent:
        if (p / "pyproject.toml").exists():
            return p
        p = p.parent
    raise RuntimeError("pyproject.toml not found; repo root could not be determined")


def _run_notify(
    *args: str,
    input_text: str | None = None,
    env: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    script = _repo_root() / "scripts" / "notify"
    child_env = dict(os.environ)
    child_env["NOTIFY_CHANNEL"] = "stdout"
    child_env.pop("NOTIFY_CHANNEL_DIR", None)
    if env:
        child_env.update(env)
    return subprocess.run(
        [str(script), *args],
        input=input_text,
        capture_output=True,
        text=True,
        check=check,
        env=child_env,
    )


def test_notify_stdout_channel_prints_message() -> None:
    result = _run_notify("build finished")
    assert result.stdout == "[generic] build finished\n"
    assert result.stderr == ""


def test_notify_accepts_stdin_message() -> None:
    result = _run_notify(
        "--stdin",
        "--event",
        "input-required",
        "--title",
        "Codex",
        input_text="Need approval",
    )
    assert result.stdout == "[input-required] Codex: Need approval\n"


def test_notify_resolves_known_kind_to_event() -> None:
    result = _run_notify("--kind", "ai_task_completed", "build finished")
    assert result.stdout == "[task_completed] build finished\n"
    assert result.stderr == ""


def test_notify_exposes_default_event_policy_to_adapters(tmp_path: Path) -> None:
    adapter = tmp_path / "capture"
    adapter.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'severity=%s\\n' \"$NOTIFY_SEVERITY\"\n"
        "printf 'verbosity=%s\\n' \"$NOTIFY_VERBOSITY\"\n",
        encoding="utf-8",
    )
    adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)

    result = _run_notify(
        "--channel",
        "capture",
        "--event",
        "needs_input",
        "Need approval",
        env={"NOTIFY_CHANNEL_DIR": str(tmp_path)},
    )

    assert result.stdout.splitlines() == [
        "event=needs_input",
        "severity=warning",
        "verbosity=critical",
    ]


def test_notify_exposes_long_task_finished_policy_to_adapters(tmp_path: Path) -> None:
    adapter = tmp_path / "capture"
    adapter.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'severity=%s\\n' \"$NOTIFY_SEVERITY\"\n"
        "printf 'verbosity=%s\\n' \"$NOTIFY_VERBOSITY\"\n",
        encoding="utf-8",
    )
    adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)

    result = _run_notify(
        "--channel",
        "capture",
        "--event",
        "long_task_finished",
        "Sync completed",
        env={"NOTIFY_CHANNEL_DIR": str(tmp_path)},
    )

    assert result.stdout.splitlines() == [
        "event=long_task_finished",
        "severity=info",
        "verbosity=normal",
    ]


def test_notify_dispatches_to_custom_adapter_directory(tmp_path: Path) -> None:
    adapter = tmp_path / "capture"
    adapter.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'stdin_payload="$(cat)"\n'
        "printf 'channel=%s\\n' \"$NOTIFY_CHANNEL_NAME\"\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'title=%s\\n' \"$NOTIFY_TITLE\"\n"
        "printf 'source=%s\\n' \"$NOTIFY_SOURCE\"\n"
        "printf 'severity=%s\\n' \"$NOTIFY_SEVERITY\"\n"
        "printf 'verbosity=%s\\n' \"$NOTIFY_VERBOSITY\"\n"
        "printf 'message=%s\\n' \"$NOTIFY_MESSAGE\"\n"
        "printf 'stdin=%s\\n' \"$stdin_payload\"\n",
        encoding="utf-8",
    )
    adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)

    result = _run_notify(
        "--channel",
        "capture",
        "--event",
        "task-complete",
        "--title",
        "CI",
        "--source",
        "pytest",
        "All green",
        env={"NOTIFY_CHANNEL_DIR": str(tmp_path)},
    )

    assert result.stdout.splitlines() == [
        "channel=capture",
        "event=task-complete",
        "title=CI",
        "source=pytest",
        "severity=info",
        "verbosity=normal",
        "message=All green",
        "stdin=All green",
    ]


def test_notify_kind_can_override_channel(tmp_path: Path) -> None:
    capture = tmp_path / "capture"
    capture.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'channel=%s\\n' \"$NOTIFY_CHANNEL_NAME\"\n",
        encoding="utf-8",
    )
    capture.chmod(capture.stat().st_mode | stat.S_IXUSR)

    discord = tmp_path / "discord"
    discord.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'channel=%s\\n' \"$NOTIFY_CHANNEL_NAME\"\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'severity=%s\\n' \"$NOTIFY_SEVERITY\"\n"
        "printf 'verbosity=%s\\n' \"$NOTIFY_VERBOSITY\"\n"
        "printf 'webhook_env=%s\\n' \"$NOTIFY_DISCORD_WEBHOOK_ENV_NAME\"\n"
        "printf 'secret_file=%s\\n' \"$NOTIFY_DISCORD_WEBHOOK_SECRET_FILE\"\n",
        encoding="utf-8",
    )
    discord.chmod(discord.stat().st_mode | stat.S_IXUSR)

    result = _run_notify(
        "--kind",
        "smoke_test",
        "smoke done",
        env={
            "NOTIFY_CHANNEL": "capture",
            "NOTIFY_CHANNEL_DIR": str(tmp_path),
        },
    )

    assert result.stdout.splitlines() == [
        "channel=discord-test",
        "event=task_completed",
        "severity=info",
        "verbosity=debug",
        "webhook_env=DISCORD_WEBHOOK_AI_STATUS_TEST",
        f"secret_file={Path.home()}/.config/secrets/discord_test_webhook.env",
    ]


def test_notify_failed_kind_uses_error_critical_policy(tmp_path: Path) -> None:
    adapter = tmp_path / "capture"
    adapter.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'severity=%s\\n' \"$NOTIFY_SEVERITY\"\n"
        "printf 'verbosity=%s\\n' \"$NOTIFY_VERBOSITY\"\n",
        encoding="utf-8",
    )
    adapter.chmod(adapter.stat().st_mode | stat.S_IXUSR)

    result = _run_notify(
        "--kind",
        "ai_task_failed",
        "Task failed",
        env={"NOTIFY_CHANNEL_DIR": str(tmp_path), "NOTIFY_CHANNEL": "capture"},
    )

    assert result.stdout.splitlines() == [
        "event=task_failed",
        "severity=error",
        "verbosity=critical",
    ]


def test_notify_channel_alias_routes_discord_test_through_discord_adapter(tmp_path: Path) -> None:
    discord = tmp_path / "discord"
    discord.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf 'channel=%s\\n' \"$NOTIFY_CHANNEL_NAME\"\n"
        "printf 'event=%s\\n' \"$NOTIFY_EVENT\"\n"
        "printf 'severity=%s\\n' \"$NOTIFY_SEVERITY\"\n"
        "printf 'verbosity=%s\\n' \"$NOTIFY_VERBOSITY\"\n"
        "printf 'webhook_env=%s\\n' \"$NOTIFY_DISCORD_WEBHOOK_ENV_NAME\"\n"
        "printf 'secret_file=%s\\n' \"$NOTIFY_DISCORD_WEBHOOK_SECRET_FILE\"\n",
        encoding="utf-8",
    )
    discord.chmod(discord.stat().st_mode | stat.S_IXUSR)

    result = _run_notify(
        "--channel",
        "discord-test",
        "--event",
        "task-complete",
        "smoke done",
        env={
            "NOTIFY_CHANNEL_DIR": str(tmp_path),
            "NOTIFY_ENV": "prod",
        },
    )

    assert result.stdout.splitlines() == [
        "channel=discord-test",
        "event=task-complete",
        "severity=info",
        "verbosity=normal",
        "webhook_env=DISCORD_WEBHOOK_AI_STATUS_TEST",
        f"secret_file={Path.home()}/.config/secrets/discord_test_webhook.env",
    ]


def test_notify_errors_for_unknown_kind() -> None:
    result = _run_notify("--kind", "missing-kind", "hello", check=False)
    assert result.returncode == 2
    assert "unknown notification kind" in result.stderr


def test_notify_errors_for_unknown_channel() -> None:
    result = _run_notify("--channel", "missing", "hello", check=False)
    assert result.returncode == 2
    assert "channel adapter not found" in result.stderr
