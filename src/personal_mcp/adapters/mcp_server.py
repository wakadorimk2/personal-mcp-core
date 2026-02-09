from personal_mcp.core.guide import load_ai_guide


def get_system_context() -> str:
    """
    System-level context provided to LLMs.
    """
    return load_ai_guide()
