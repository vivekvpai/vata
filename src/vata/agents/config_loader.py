import json
import shutil
from pathlib import Path
from typing import Dict, Any

def get_default_config() -> Dict[str, Any]:
    """Load and return the default AI agents configuration block from user directory."""
    user_config_dir = Path.home() / ".vata"
    user_config_dir.mkdir(parents=True, exist_ok=True)
    config_path = user_config_dir / "agents_config.json"
    
    # If the user doesn't have a config yet, seed it from our package defaults
    if not config_path.exists():
        default_packaged_config = Path(__file__).parent / "config.json"
        if default_packaged_config.exists():
            shutil.copy(default_packaged_config, config_path)
        else:
            raise FileNotFoundError(f"Configuration file not found at {default_packaged_config}")
        
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)

def get_agent_config(agent_key: str) -> Dict[str, Any]:
    """Retrieve configuration for a specific agent by its key (e.g., 'suggestion_ai')."""
    config_data = get_default_config()
    agents = config_data.get("agents", {})
    if agent_key not in agents:
        raise KeyError(f"Agent configuration for '{agent_key}' not found.")
    return agents[agent_key]
