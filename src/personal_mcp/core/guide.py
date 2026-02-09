from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
GUIDE_PATH = ROOT / "AI_GUIDE.md"


def load_ai_guide() -> str:
    """
    Load AI_GUIDE.md as plain text.
    This is intended to be injected as system-level context.
    """
    return GUIDE_PATH.read_text(encoding="utf-8")
