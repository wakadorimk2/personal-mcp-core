from pathlib import Path

from personal_mcp.storage.path import resolve_data_dir


def test_explicit_arg_takes_priority(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PERSONAL_MCP_DATA_DIR", str(tmp_path / "env"))

    result = resolve_data_dir(str(tmp_path / "explicit"))

    assert result == str(tmp_path / "explicit")


def test_env_var_takes_priority_over_xdg(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PERSONAL_MCP_DATA_DIR", str(tmp_path / "env"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    result = resolve_data_dir(None)

    assert result == str(tmp_path / "env")


def test_xdg_data_home_used_when_set(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("PERSONAL_MCP_DATA_DIR", raising=False)
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))

    result = resolve_data_dir(None)

    assert result == str(tmp_path / "xdg" / "personal-mcp")


def test_fallback_to_home_local_share(monkeypatch) -> None:
    monkeypatch.delenv("PERSONAL_MCP_DATA_DIR", raising=False)
    monkeypatch.delenv("XDG_DATA_HOME", raising=False)

    result = resolve_data_dir(None)

    assert result == str(Path.home() / ".local" / "share" / "personal-mcp")
