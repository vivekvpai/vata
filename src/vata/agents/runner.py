import litellm
from typing import Optional, Dict, Any
from .config_loader import get_agent_config

async def run_agent(agent_key: str, user_prompt: str, override_config: Optional[Dict[str, Any]] = None) -> str:
    """
    Execute an AI agent call using LiteLLM.
    
    Args:
        agent_key: The key in config.json (e.g., 'suggestion_ai').
        user_prompt: The prompt from the user/application.
        override_config: Optional dictionary to override default agent parameters.
        
    Returns:
        The text response from the model.
    """
    # Load default configuration
    config = get_agent_config(agent_key)
    
    # Merge with optional overrides
    if override_config:
        config.update(override_config)
    
    # Extract parameters
    model = config.get("model")
    api_key = config.get("api_key")
    api_base = config.get("api_base")
    system_prompt = config.get("system_prompt", "You are a helpful assistant.")
    parameters = config.get("parameters", {})
    
    # Prepare messages
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    # Execute call via LiteLLM
    # Note: api_base and api_key are passed if present; LiteLLM defaults to env vars if missing.
    response = await litellm.acompletion(
        model=model,
        messages=messages,
        api_key=api_key if api_key else None,
        api_base=api_base if api_base else None,
        **parameters
    )
    
    return response.choices[0].message.content
