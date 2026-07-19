"""Interactive first-run setup: `vata-mcp setup`.

Walks a new user through picking a MongoDB (local or Atlas), optionally an
LLM key, an access token, and an optional /vata-clean password — then
writes everything to the persistent config file (see config.py) and
prints a ready-to-paste MCP client config block.

Plain input()-based wizard, no extra dependency — this only needs to run
once per install, doesn't need a fancy TUI.
"""

import secrets
import sys

from . import config


def _ask(prompt: str, default: str | None = None) -> str:
    suffix = f" [{default}]" if default else ""
    raw = input(f"{prompt}{suffix}: ").strip()
    return raw or (default or "")


def _ask_yes_no(prompt: str, default_yes: bool) -> bool:
    default_label = "Y/n" if default_yes else "y/N"
    raw = input(f"{prompt} [{default_label}]: ").strip().lower()
    if not raw:
        return default_yes
    return raw in ("y", "yes")


def _validate_mongo_uri(uri: str) -> str | None:
    """Returns an error message, or None if the connection works."""
    try:
        from pymongo import MongoClient

        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        client.close()
        return None
    except Exception as e:
        return str(e)


def _step_database() -> str | None:
    print("\n--- Database ---")
    print("Vata needs a MongoDB database to store your saved links/notes.")
    use_atlas = _ask_yes_no(
        "Use a MongoDB Atlas connection string? (No = local MongoDB on this machine)",
        default_yes=False,
    )

    if use_atlas:
        while True:
            uri = _ask("Paste your Atlas connection string (mongodb+srv://...)")
            if not uri:
                print("  (skipped — you can set this later)")
                return None
            print("  Checking connection...")
            error = _validate_mongo_uri(uri)
            if error is None:
                print("  Connected successfully.")
                return uri
            print(f"  Could not connect: {error}")
            if not _ask_yes_no("  Try a different connection string?", default_yes=True):
                return None
    else:
        default_uri = "mongodb://localhost:27017"
        print(f"  Checking for local MongoDB at {default_uri} ...")
        error = _validate_mongo_uri(default_uri)
        if error is None:
            print("  Found a local MongoDB instance.")
            return default_uri
        print(f"  No local MongoDB found ({error}).")
        print("  Install it, then re-run `vata-mcp setup`. One-line installs:")
        print("    Windows:  winget install MongoDB.Server")
        print("    macOS:    brew install mongodb-community")
        print("    Linux:    see https://www.mongodb.com/docs/manual/administration/install-on-linux/")
        if _ask_yes_no("  Continue without a database for now? (uses a non-persistent in-memory DB)", default_yes=True):
            return None
        sys.exit(1)


def _step_ai() -> str | None:
    print("\n--- AI ---")
    print(
        "Vata normally lets whichever LLM is driving your chat session (Claude, etc.)\n"
        "decide categories/titles/tags for free, as part of ordinary tool use — no\n"
        "API key needed for that. VATA_LLM_MODEL below is a fallback only, for a\n"
        "caller that can't reason for itself (a script calling the tool directly)."
    )
    want_llm = _ask_yes_no("Set a fallback LLM model now?", default_yes=False)
    if not want_llm:
        return None
    model = _ask("Model string (litellm format, e.g. gpt-4o-mini)")
    if model:
        print("  Remember to also set your provider's own API key env var (e.g. OPENAI_API_KEY) — Vata does not store or proxy that key.")
    return model or None


def _step_token() -> str | None:
    print("\n--- Access token ---")
    print("Only needed if you'll run this over HTTP and expose it beyond your own machine.")
    want_token = _ask_yes_no("Generate an access token now?", default_yes=False)
    if not want_token:
        return None
    token = secrets.token_urlsafe(32)
    print(f"  Generated: {token}")
    print("  Save this now — it will only be shown once.")
    return token


def _step_clean_password() -> str | None:
    print("\n--- Full database wipe (/vata-clean) ---")
    want = _ask_yes_no("Enable the /vata-clean command (wipes everything, password-gated)?", default_yes=False)
    if not want:
        return None
    password = _ask("Set a password for it")
    return password or None


def _print_client_config() -> None:
    print("\n--- MCP client config ---")
    print("Paste this into your MCP client's config (e.g. Claude Desktop/Code):\n")
    print("{")
    print('  "mcpServers": {')
    print('    "vata": {')
    print('      "command": "vata-mcp"')
    print("    }")
    print("  }")
    print("}")
    print(
        "\nEnvironment variables are already saved to your config file, so no `env` "
        "block is needed above unless you want to override something per-client.\n"
        "If `vata-mcp` isn't on your PATH (e.g. installed inside a venv without "
        "activating it), use the full path to it instead, or run via "
        f"{sys.executable!r} with args [\"-m\", \"vata_mcp.server\"]."
    )


def run() -> None:
    print("=== Vata MCP setup ===")
    print(f"Config file: {config.config_file_path()}\n")

    mongo_uri = _step_database()
    llm_model = _step_ai()
    token = _step_token()
    clean_password = _step_clean_password()

    values = {}
    if mongo_uri:
        values["VATA_MONGODB_URI"] = mongo_uri
    if llm_model:
        values["VATA_LLM_MODEL"] = llm_model
    if token:
        values["VATA_MCP_TOKEN"] = token
    if clean_password:
        values["VATA_CLEAN_PASSWORD"] = clean_password

    if values:
        path = config.write_config(values)
        print(f"\nSaved configuration to {path}")
    else:
        print("\nNothing to save — running with defaults (in-memory DB, no auth, no LLM).")

    _print_client_config()
    print("\nSetup complete. Run `vata-mcp` to start the server, or just configure your MCP client to launch it for you.")


if __name__ == "__main__":
    run()
