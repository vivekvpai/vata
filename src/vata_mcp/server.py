"""Vata MCP server.

Exposes the full Vata operation set as MCP tools, plus slash prompts
(`vata-save`, `vata-get`, `vata-find`, `vata-stats`, `vata-list-categories`,
`vata-describe`) for the common path. Categories are fully AI-managed:
`vata_save` never takes a category argument, and new categories get an
AI-written description alongside the name.

Run locally (dummy in-memory Mongo, heuristic AI, no external services):
    python -m vata_mcp.server

Point at real MongoDB Atlas + a real LLM later via env vars:
    VATA_MONGODB_URI=mongodb+srv://...   (else falls back to mongomock)
    VATA_LLM_MODEL=gpt-4o-mini            (else falls back to BM25/heuristic)

Protect the HTTP transport with a shared bearer token (required once this
is reachable on a public URL):
    VATA_MCP_TOKEN=some-long-random-secret  (unset = auth disabled, stdio default)
"""

import os

from fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Literal

from .auth import build_auth_provider
from .services import ai_service, category_service, decision_service, storage
from .services.category_service import VataConflictError, VataNotFoundError

mcp = FastMCP("Vata", auth=build_auth_provider())


def _error(exc: Exception) -> dict:
    return {"error": str(exc), "error_type": type(exc).__name__}


# --- Tools: primary verbs ---


@mcp.tool
async def vata_save(
    content: Annotated[str, Field(description="The raw content to save.")],
    summary: Annotated[str | None, Field(description="Optional summary override. AI generates one if omitted.")] = None,
    tags: Annotated[list[str] | None, Field(description="Optional tag list override. AI generates tags if omitted.")] = None,
) -> dict:
    """Save content to Vata. The category is decided entirely by AI —
    never pass a category. AI reuses an existing category if the content
    fits, or creates a new one automatically, with an AI-written description."""
    decision = await ai_service.decide_category_and_metadata(content, summary, tags)
    category_doc = category_service.resolve_or_create_category(
        decision["category"], decision.get("category_description", "")
    )
    result = category_service.add_asset_to_category_record(
        category_doc["_id"], content, decision["summary"], decision["tags"]
    )
    return {
        "message": "Saved",
        "asset_id": result["asset_id"],
        "category_id": category_doc["_id"],
        "category": category_doc["category"],
        "summary": decision["summary"],
        "tags": decision["tags"],
    }


@mcp.tool
async def vata_get(
    asset_id: Annotated[str | None, Field(description="Fetch one specific asset by id.")] = None,
    category_id: Annotated[str | None, Field(description="List summaries of assets in one category.")] = None,
) -> dict:
    """Retrieve saved content. No args -> list all categories (use
    vata_list_categories for a dedicated table view instead). category_id
    only -> summaries of everything in it, table-ready (name, summary,
    count). asset_id -> full content of one asset. Prefer vata_find for
    retrieval by meaning rather than by id."""
    try:
        if asset_id:
            return category_service.get_asset_record(asset_id)
        if category_id:
            return category_service.get_category_summary(category_id)
        return category_service.list_categories_record()
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_find(
    query: Annotated[str, Field(description="Natural-language search query.")],
) -> dict:
    """Search saved content by meaning. Ranks categories then assets via
    BM25, with an optional LLM re-rank pass for match reasons when an LLM
    is configured. This is the primary retrieval tool."""
    return decision_service.evaluate_nodes_for_query(query)


@mcp.tool
async def vata_suggest(
    content: Annotated[str, Field(description="Content to preview AI filing decisions for, without saving.")],
    summary: Annotated[str | None, Field(description="Optional summary override.")] = None,
    tags: Annotated[list[str] | None, Field(description="Optional tag override.")] = None,
) -> dict:
    """Preview what vata_save would decide (category/summary/tags) without
    writing anything. Useful for transparency/debugging."""
    return await ai_service.fetch_suggestions(content, summary, tags)


@mcp.tool
async def vata_stats() -> dict:
    """Return overall Vata metrics: total categories, total assets, and the
    running server version."""
    return category_service.get_stats()


@mcp.tool
async def vata_describe() -> dict:
    """Describe this Vata MCP server: what it is, every tool and prompt it
    exposes, and the current backend configuration (storage, AI, auth).
    Use this when asked "what can Vata do" or "how is Vata configured"."""
    tools = await mcp.list_tools()
    prompts = await mcp.list_prompts()
    return {
        "name": "Vata MCP",
        "description": (
            "A personal knowledge store exposed as MCP tools/prompts. Save "
            "arbitrary content with vata_save — AI decides which category it "
            "belongs to (creating one with a written description if none "
            "fits) so you never manage categories by hand. Retrieve by "
            "meaning with vata_find, by id with vata_get, or browse "
            "everything with vata_list_categories/vata_stats."
        ),
        "version": category_service.VATA_MCP_VERSION,
        "tools": sorted(t.name for t in tools),
        "prompts": sorted(p.name for p in prompts),
        "storage_backend": storage.backend_info(),
        "ai_backend": ai_service.backend_info(),
        "auth_enabled": bool(os.getenv("VATA_MCP_TOKEN")),
    }


@mcp.tool
async def vata_list_categories() -> dict:
    """List every category with its name, AI-written description, and
    asset count. Present this as a table: Category | Description | Assets."""
    return category_service.list_categories_record()


# --- Tools: edit / delete / link (tool-only, no slash prompt) ---


@mcp.tool
async def vata_edit_asset(
    asset_id: Annotated[str, Field(description="Asset to edit.")],
    category_id: Annotated[str, Field(description="One category this asset currently belongs to.")],
    main_content: Annotated[str | None, Field(description="New content, if changing.")] = None,
    summary: Annotated[str | None, Field(description="New summary, if changing.")] = None,
    tags: Annotated[list[str] | None, Field(description="New tag list, if changing.")] = None,
) -> dict:
    """Patch an existing asset's content/summary/tags."""
    try:
        return category_service.update_asset_in_record(
            category_id, asset_id, {"main_content": main_content, "summary": summary, "tags": tags}
        )
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_delete_asset(
    category_id: Annotated[str, Field(description="Category the asset belongs to.")],
    asset_id: Annotated[str, Field(description="Asset to delete.")],
    confirm: Annotated[Literal[True], Field(description="Must be explicitly true. Destructive action.")],
) -> dict:
    """Delete an asset. Unlinks it from category_id; if that was its only
    category, the asset is hard-deleted entirely. Requires confirm=true."""
    try:
        return category_service.delete_asset_from_record(category_id, asset_id)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_delete_category(
    category_id: Annotated[str, Field(description="Category to delete.")],
    confirm: Annotated[Literal[True], Field(description="Must be explicitly true. Destructive action.")],
) -> dict:
    """Delete a category. Any assets with no other category membership are
    hard-deleted too. Requires confirm=true."""
    try:
        return category_service.delete_category_record(category_id)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_rename_category(
    category_id: Annotated[str, Field(description="Category to rename.")],
    new_name: Annotated[str, Field(description="New human-readable name.")],
) -> dict:
    """Rename a category. This changes its category_id (IDs are derived
    from name + timestamp). Mostly for AI/admin use to consolidate
    near-duplicate auto-created categories."""
    try:
        return category_service.rename_category_record(category_id, new_name)
    except (VataNotFoundError, VataConflictError) as e:
        return _error(e)


@mcp.tool
async def vata_edit_category(
    category_id: Annotated[str, Field(description="Category whose description will be updated.")],
    description: Annotated[str, Field(description="New one-sentence description of what belongs in this category.")],
) -> dict:
    """Edit a category's description (name changes go through
    vata_rename_category instead)."""
    try:
        return category_service.edit_category_description(category_id, description)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_link_asset(
    category_id: Annotated[str, Field(description="Category to attach the asset to.")],
    asset_id: Annotated[str, Field(description="Asset to attach.")],
) -> dict:
    """Attach an existing asset to an additional category (many-to-many)."""
    try:
        return category_service.link_asset_to_category(category_id, asset_id)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_unlink_asset(
    category_id: Annotated[str, Field(description="Category to detach the asset from.")],
    asset_id: Annotated[str, Field(description="Asset to detach.")],
) -> dict:
    """Detach an asset from one category without necessarily deleting it —
    it's hard-deleted only if this was its last remaining category."""
    try:
        return category_service.unlink_asset_from_category(category_id, asset_id)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_replace_category(
    category_id: Annotated[str, Field(description="Category whose contents will be wholesale replaced.")],
    data: Annotated[
        dict,
        Field(description='Map of arbitrary keys to {"main_content", "summary"?, "tags"?} objects to become the new members.'),
    ],
) -> dict:
    """Bulk-replace a category's members: unlinks everything currently in
    it, then creates new assets from `data`. Rarely used directly; kept for
    parity with bulk-import style flows."""
    try:
        return category_service.replace_category_record(category_id, data)
    except VataNotFoundError as e:
        return _error(e)


# --- Prompts: typed slash-command entry points ---


@mcp.prompt(name="vata-save")
def vata_save_prompt(content: str) -> str:
    """Save something to Vata (AI files it under a category automatically)."""
    return (
        f"Call the vata_save tool with content={content!r}. "
        "Do not ask the user for a category — the tool decides that on its own. "
        "Report back the category it was filed under."
    )


@mcp.prompt(name="vata-get")
def vata_get_prompt(what: str = "") -> str:
    """Retrieve something previously saved to Vata."""
    if what:
        return (
            f"The user wants to retrieve: {what!r}. "
            "If this looks like a specific asset id, call vata_get with asset_id. "
            "If it looks like a category id, call vata_get with category_id and "
            "present the result's items as a table: Summary | Tags | Updated. "
            "Otherwise, prefer calling vata_find with this as the query instead, "
            "since vata_get requires an id and vata_find searches by meaning."
        )
    return "Call the vata_list_categories tool and present the result as a table: Category | Description | Assets."


@mcp.prompt(name="vata-find")
def vata_find_prompt(query: str) -> str:
    """Search everything saved to Vata by meaning."""
    return f"Call the vata_find tool with query={query!r} and present the ranked results with their match reasons."


@mcp.prompt(name="vata-stats")
def vata_stats_prompt() -> str:
    """Show Vata's overall metrics: category count, asset count, version."""
    return "Call the vata_stats tool and report the category count, asset count, and version."


@mcp.prompt(name="vata-list-categories")
def vata_list_categories_prompt() -> str:
    """List all categories in a table: name, description, asset count."""
    return "Call the vata_list_categories tool and present the result as a table: Category | Description | Assets."


@mcp.prompt(name="vata-describe")
def vata_describe_prompt() -> str:
    """Describe what this Vata MCP server is and how it's configured."""
    return "Call the vata_describe tool and summarize what Vata is, its available tools/prompts, and its current storage/AI/auth configuration."


def main() -> None:
    transport = os.getenv("VATA_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        if not os.getenv("VATA_MCP_TOKEN"):
            print(
                "[vata-mcp] WARNING: VATA_MCP_TOKEN is not set — this HTTP server "
                "has NO auth and anyone with the URL can call every tool, "
                "including deletes. Set VATA_MCP_TOKEN before exposing this publicly."
            )
        host = os.getenv("VATA_MCP_HOST", "0.0.0.0")
        # Render/Railway/etc inject PORT; fall back to VATA_MCP_PORT for local runs.
        port = int(os.getenv("PORT") or os.getenv("VATA_MCP_PORT", "8765"))
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
