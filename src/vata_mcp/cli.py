"""Entry point dispatcher for the `vata-mcp` console script.

`vata-mcp`        -> runs the MCP server (server.main())
`vata-mcp setup`  -> runs the interactive setup wizard
"""

import sys


def main() -> None:
    args = sys.argv[1:]
    if args and args[0] == "setup":
        from .setup_wizard import run

        run()
        return

    from .server import main as run_server

    run_server()


if __name__ == "__main__":
    main()
