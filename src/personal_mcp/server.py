from personal_mcp.adapters.mcp_server import get_system_context


def main():
    # Placeholder entrypoint
    context = get_system_context()
    print("System context loaded.")
    print(f"Length: {len(context)} characters")


if __name__ == "__main__":
    main()
