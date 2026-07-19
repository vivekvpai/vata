"""Layered configuration: environment variable → config file → default.

Environment variables always win when set, so CI/Docker/power-user setups
that already export vars keep working unchanged. Everyone else gets a
persistent config file written once by `vata-mcp setup` instead of having
to export the same variables every terminal session.

Config file lives in the OS-appropriate per-user config directory:
    Windows:  %APPDATA%\\vata-mcp\\config.json
    macOS:    ~/Library/Application Support/vata-mcp/config.json
    Linux:    $XDG_CONFIG_HOME/vata-mcp/config.json (or ~/.config/vata-mcp/config.json)
"""

import json
import os
import sys
from pathlib import Path

_KNOWN_KEYS = (
    "VATA_MONGODB_URI",
    "VATA_MONGODB_DB",
    "VATA_LLM_MODEL",
    "VATA_MCP_TOKEN",
    "VATA_CLEAN_PASSWORD",
    "VATA_MCP_TRANSPORT",
    "VATA_MCP_HOST",
    "VATA_MCP_PORT",
)


def config_dir() -> Path:
    if sys.platform == "win32":
        base = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "vata-mcp"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "vata-mcp"
    base = os.getenv("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "vata-mcp"


def config_file_path() -> Path:
    return config_dir() / "config.json"


def _load_file() -> dict:
    path = config_file_path()
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError) as e:
        print(f"[vata-mcp] config: failed to read {path} ({e}) — ignoring, using env vars/defaults only")
        return {}


_file_cache: dict | None = None


def _file_config() -> dict:
    global _file_cache
    if _file_cache is None:
        _file_cache = _load_file()
    return _file_cache


def get(key: str, default: str | None = None) -> str | None:
    """Env var, if set and non-empty, wins. Else the config file. Else default."""
    env_value = os.getenv(key)
    if env_value:
        return env_value
    file_value = _file_config().get(key)
    if file_value:
        return file_value
    return default


def write_config(values: dict) -> Path:
    """Write (merge into) the config file. Only known keys with a
    non-None/non-empty value are persisted — clears a key if given ""."""
    path = config_file_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    current = _load_file()
    for key, value in values.items():
        if key not in _KNOWN_KEYS:
            raise ValueError(f"Unknown config key: {key!r}")
        if value:
            current[key] = value
        else:
            current.pop(key, None)
    with path.open("w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
    global _file_cache
    _file_cache = current
    return path


def describe_source(key: str) -> str:
    """For diagnostics: where would `get(key)` currently read from?"""
    if os.getenv(key):
        return "environment variable"
    if _file_config().get(key):
        return f"config file ({config_file_path()})"
    return "default"
