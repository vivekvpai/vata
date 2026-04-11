import json
from fastapi import HTTPException
from ..agents import run_agent
from .category_service import load_category_registry

async def fetch_ai_suggestions(main_content: str, summary: str | None, tags: list[str]) -> dict:
    """Prepare context and call the Suggestion AI agent."""
    registry = load_category_registry()
    existing_categories = list(registry.keys())

    context = f"Main Content: {main_content}\n"
    if summary:
        context += f"Current Summary: {summary}\n"
    if tags:
        context += f"Current Tags: {', '.join(tags)}\n"
    
    context += f"\nExisting Categories in the system: {', '.join(existing_categories)}\n"
    context += "\nEvaluate all the above information collectively to provide the most coherent and unified suggestions possible."

    try:
        raw_response = await run_agent("suggestion_ai", context)
        # Attempt to parse json from model
        clean_json = raw_response.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json.split("```json", 1)[1].split("```", 1)[0].strip()
        elif clean_json.startswith("```"):
            clean_json = clean_json.split("```", 1)[1].split("```", 1)[0].strip()

        return json.loads(clean_json)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Agent Error: {str(e)}")
