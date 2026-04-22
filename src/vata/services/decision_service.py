import json
from pathlib import Path
from typing import List, Dict

from langchain_community.chat_models import ChatLiteLLM
from langchain_core.messages import SystemMessage, HumanMessage

from ..agents.config_loader import get_agent_config
from .category_service import load_category_registry, read_json_file, DATA_DIR


def evaluate_nodes_for_query(query: str) -> Dict:
    """Finds assets matching the query using a two-pass category-first traversal."""
    config = get_agent_config("decision_ai")

    chat_model = ChatLiteLLM(
        model=config.get("model"),
        api_key=config.get("api_key") or None,
        api_base=config.get("api_base") or None,
        temperature=config.get("parameters", {}).get("temperature", 0.1),
        max_tokens=config.get("parameters", {}).get("max_tokens", 1000),
    )

    # --- Pass 1: Identify Relevant Categories ---
    registry = load_category_registry()
    category_overviews = []

    for category_id, base_name in registry.items():
        file_path = DATA_DIR / f"{category_id}.json"
        if file_path.exists():
            payload = read_json_file(file_path)
            assets = payload.get("data", {})

            # Aggregate metadata on-the-fly
            all_summaries = " ".join([a.get("summary", "") for a in assets.values()])
            all_tags = []
            for a in assets.values():
                all_tags.extend(a.get("tags", []))

            category_overviews.append(
                {
                    "category_id": category_id,
                    "category_name": payload.get("category", base_name),
                    "keywords": list(set(all_tags))[:20],  # Limit keywords
                    "summary_snippet": all_summaries[:500],  # Snippet for context
                }
            )

    if not category_overviews:
        return {
            "message": "Decision generated",
            "count": 0,
            "data": []
        }

    # Prompt LLM for relevant categories
    cat_system_prompt = 'You are a category classification engine. Given a User Query and a list of Categories (with keywords and summaries), determine which categories are relevant. Return strictly a JSON array of category IDs, e.g. ["id1", "id2"]. Return [] if none match.'
    cat_user_message = (
        f"Query: {query}\n\nCategories:\n{json.dumps(category_overviews, indent=2)}"
    )

    try:
        cat_response = chat_model.invoke(
            [
                SystemMessage(content=cat_system_prompt),
                HumanMessage(content=cat_user_message),
            ]
        )
        cat_res_content = clean_json_response(cat_response.content)
        relevant_category_ids = json.loads(cat_res_content)
        if not isinstance(relevant_category_ids, list):
            relevant_category_ids = []
    except Exception as e:
        print(f"Failed to identify relevant categories: {e}")
        relevant_category_ids = []

    if not relevant_category_ids:
        # Fallback: if Pass 1 fails to find anything but we have categories, we might want to try all?
        # But per user request, we go inside relevant categories. If none relevant, return empty.
        return {
            "message": "Decision generated",
            "count": 0,
            "data": []
        }

    # --- Pass 2: Identify Relevant Assets within identified categories ---
    final_relevant_results = []
    asset_system_prompt = config.get("system_prompt", "")

    for category_id in relevant_category_ids:
        file_path = DATA_DIR / f"{category_id}.json"
        if not file_path.exists():
            continue

        payload = read_json_file(file_path)
        category_name = payload.get("category", "unknown")
        assets_dict = payload.get("data", {})

        category_assets = []
        for asset_id, asset_data in assets_dict.items():
            category_assets.append(
                {
                    "asset_id": asset_id,
                    "category": category_name,
                    "summary": asset_data.get("summary", ""),
                    "tags": asset_data.get("tags", []),
                    "content_snippet": asset_data.get("main_content", "")[:200],
                }
            )

        if not category_assets:
            continue

        # Process this category's assets
        # Chunks of 15 as before
        for i in range(0, len(category_assets), 15):
            chunk = category_assets[i : i + 15]
            nodes_context = json.dumps(chunk, indent=2)
            user_msg = f"Query: {query}\n\nNodes in category '{category_name}':\n{nodes_context}"

            try:
                response = chat_model.invoke(
                    [
                        SystemMessage(content=asset_system_prompt),
                        HumanMessage(content=user_msg),
                    ]
                )
                res_content = clean_json_response(response.content)
                parsed = json.loads(res_content)

                if isinstance(parsed, list):
                    for match in parsed:
                        matched_id = str(match.get("asset_id"))
                        node = next(
                            (n for n in chunk if n["asset_id"] == matched_id), None
                        )
                        if node:
                            final_relevant_results.append(
                                {
                                    "asset_id": node["asset_id"],
                                    "category": node["category"],
                                    "category_id": category_id,
                                    "summary": node["summary"],
                                    "tags": node["tags"],
                                    "match_reason": match.get("reason", ""),
                                    "content_snippet": node["content_snippet"],
                                }
                            )
            except Exception as e:
                print(f"Failed to parse assets for category {category_id}: {e}")
                continue

    return {
        "message": "Decision generated",
        "count": len(final_relevant_results),
        "data": final_relevant_results,
    }


def clean_json_response(content: str) -> str:
    """Cleans markdown wrappers and whitespace from LLM JSON response."""
    content = content.strip()
    if content.startswith("```json"):
        content = content.split("```json", 1)[1].split("```", 1)[0].strip()
    elif content.startswith("```"):
        content = content.split("```", 1)[1].split("```", 1)[0].strip()
    return content
