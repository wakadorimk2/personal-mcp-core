# src/personal_mcp/server.py
def main() -> int:
    # TODO: replace with real MCP server wiring later
    from personal_mcp.adapters.mcp_server import get_system_context
    text = get_system_context()
    print(f"loaded system context: {len(text)} chars")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())