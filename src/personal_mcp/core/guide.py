from __future__ import annotations

from importlib import resources


def load_ai_guide() -> str:
    """
    Load AI_GUIDE.md as plain text.

    Intended use:
    - Inject as system-level context for LLM/tool clients.
    - Prefer packaged resource for installed environments.
    - Fallback to repo-root AI_GUIDE.md for development checkouts.
    """
    # 1) Primary: packaged resource
    try:
        return (
            resources.files("personal_mcp")
            .joinpath("AI_GUIDE.md")
            .read_text(encoding="utf-8")
        )
    except (FileNotFoundError, OSError, UnicodeDecodeError):
        pass

    # 2) Fallback: repo-root file (dev)
    from pathlib import Path

    # core/guide.py -> personal_mcp/core -> src -> repo root
    guide_path = Path(__file__).resolve().parents[3] / "AI_GUIDE.md"
    try:
        return guide_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"AI guide file not found. Tried packaged resource and {guide_path}."
        ) from exc
    except UnicodeDecodeError as exc:
        raise RuntimeError(
            f"Failed to decode AI guide at {guide_path} using UTF-8."
        ) from exc
