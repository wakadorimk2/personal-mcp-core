from __future__ import annotations

import json
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


def _run_notify(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    script = _repo_root() / "scripts" / "notify"
    return subprocess.run(
        [str(script), *args],
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, **(env or {})},
    )


def _write_fake_curl(tmp_path: Path) -> tuple[Path, Path]:
    curl = tmp_path / "curl"
    args_file = tmp_path / "curl-args.txt"
    curl.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'printf \'%s\\n\' "$@" > "$FAKE_CURL_ARGS_FILE"\n'
        "printf '%s' \"${FAKE_CURL_STDERR:-}\" >&2\n"
        "printf '%s' \"${FAKE_CURL_STDOUT:-204}\"\n"
        'exit "${FAKE_CURL_EXIT_CODE:-0}"\n',
        encoding="utf-8",
    )
    curl.chmod(curl.stat().st_mode | stat.S_IXUSR)
    return curl, args_file


def _fake_curl_env(tmp_path: Path, args_file: Path) -> dict[str, str]:
    return {
        "PATH": f"{tmp_path}:/usr/bin:/bin",
        "FAKE_CURL_ARGS_FILE": str(args_file),
    }


def _write_secret_file(home: Path, content: str) -> Path:
    secret_file = home / ".config" / "secrets" / "discord_webhook.env"
    secret_file.parent.mkdir(parents=True, exist_ok=True)
    secret_file.write_text(content, encoding="utf-8")
    return secret_file


def _load_payload(args_file: Path) -> tuple[list[str], dict[str, object]]:
    args = args_file.read_text(encoding="utf-8").splitlines()
    payload = json.loads(args[args.index("--data") + 1])
    return args, payload


def test_notify_discord_channel_posts_expected_payload(tmp_path: Path) -> None:
    _, args_file = _write_fake_curl(tmp_path)
    env = {
        **_fake_curl_env(tmp_path, args_file),
        "DISCORD_WEBHOOK_URL": "https://discord.example/webhook",
        "DISCORD_WEBHOOK_USERNAME": "Codex",
        "DISCORD_WEBHOOK_AVATAR_URL": "https://example.com/avatar.png",
    }

    result = _run_notify(
        "--channel",
        "discord",
        "--event",
        "task_completed",
        "--title",
        "Issue #238",
        "--source",
        "codex-tui",
        "Discord adapter ready",
        env=env,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    args, payload = _load_payload(args_file)
    assert args[-1] == "https://discord.example/webhook"
    assert payload == {
        "content": "**Issue #238**\nDiscord adapter ready\n[`task_completed` from `codex-tui`]",
        "username": "Codex",
        "avatar_url": "https://example.com/avatar.png",
    }


def test_notify_discord_channel_uses_secret_file_fallback(tmp_path: Path) -> None:
    _, args_file = _write_fake_curl(tmp_path)
    home = tmp_path / "home"
    _write_secret_file(home, 'export DISCORD_WEBHOOK_URL="https://discord.example/from-file"\n')

    result = _run_notify(
        "--channel",
        "discord",
        "hello",
        env={
            **_fake_curl_env(tmp_path, args_file),
            "HOME": str(home),
        },
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    args, payload = _load_payload(args_file)
    assert args[-1] == "https://discord.example/from-file"
    assert payload == {
        "content": "hello\n[`generic`]",
    }


def test_notify_discord_channel_prefers_env_over_secret_file(tmp_path: Path) -> None:
    _, args_file = _write_fake_curl(tmp_path)
    home = tmp_path / "home"
    _write_secret_file(home, 'export DISCORD_WEBHOOK_URL="https://discord.example/from-file"\n')

    result = _run_notify(
        "--channel",
        "discord",
        "hello",
        env={
            **_fake_curl_env(tmp_path, args_file),
            "HOME": str(home),
            "DISCORD_WEBHOOK_URL": "https://discord.example/from-env",
        },
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
    args, _ = _load_payload(args_file)
    assert args[-1] == "https://discord.example/from-env"


def test_notify_discord_channel_errors_without_env_or_secret_file(tmp_path: Path) -> None:
    _, args_file = _write_fake_curl(tmp_path)
    home = tmp_path / "home"

    result = _run_notify(
        "--channel",
        "discord",
        "hello",
        env={
            **_fake_curl_env(tmp_path, args_file),
            "HOME": str(home),
        },
    )

    assert result.returncode == 2
    assert "DISCORD_WEBHOOK_URL is required" in result.stderr
    assert not args_file.exists()


def test_notify_discord_channel_errors_for_http_failure(tmp_path: Path) -> None:
    _, args_file = _write_fake_curl(tmp_path)
    env = {
        **_fake_curl_env(tmp_path, args_file),
        "DISCORD_WEBHOOK_URL": "https://discord.example/webhook",
        "FAKE_CURL_STDOUT": "500",
    }

    result = _run_notify("--channel", "discord", "hello", env=env)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "HTTP 500" in result.stderr


def test_notify_discord_channel_errors_for_transport_failure(tmp_path: Path) -> None:
    _, args_file = _write_fake_curl(tmp_path)
    env = {
        **_fake_curl_env(tmp_path, args_file),
        "DISCORD_WEBHOOK_URL": "https://discord.example/webhook",
        "FAKE_CURL_STDOUT": "",
        "FAKE_CURL_STDERR": "curl: (7) failed to connect",
        "FAKE_CURL_EXIT_CODE": "7",
    }

    result = _run_notify("--channel", "discord", "hello", env=env)

    assert result.returncode == 1
    assert result.stdout == ""
    assert "curl: (7) failed to connect" in result.stderr
    assert "webhook POST failed" in result.stderr
