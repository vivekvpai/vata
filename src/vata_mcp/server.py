"""Vata MCP server.

A personal link/notes archive exposed as MCP tools + slash prompts:
`vata-save`, `vata-list-categories`, `vata-list-assets`, `vata-edit-category`,
`vata-edit-asset`, `vata-delete-category`, `vata-delete-asset`, `vata-find`,
`vata-describe`, `vata-stats`, `vata-clean`.

Categories are managed by whichever LLM is driving the MCP session — the
calling assistant is expected to call `vata_list_categories`, decide
title/category/description/tags itself, and pass them explicitly into
`vata_save`. Fields left blank fall back to `VATA_LLM_MODEL` or a local
heuristic, for callers that can't reason for themselves. Each asset
belongs to exactly one category — deleting a category deletes its assets
too. Assets are addressable by id or by title.

Run locally (dummy in-memory Mongo, heuristic AI, no external services):
    python -m vata_mcp.server

Point at real MongoDB Atlas + a real LLM later via env vars:
    VATA_MONGODB_URI=mongodb+srv://...   (else falls back to mongomock)
    VATA_LLM_MODEL=gpt-4o-mini            (else falls back to BM25/heuristic)

Protect the HTTP transport with a shared bearer token (required once this
is reachable on a public URL):
    VATA_MCP_TOKEN=some-long-random-secret  (unset = auth disabled, stdio default)

vata_clean (full database wipe) requires a separate password, set via:
    VATA_CLEAN_PASSWORD=some-password  (unset = vata_clean refuses to run at all)
"""

import hmac
import os

from fastmcp import FastMCP
from pydantic import Field
from typing import Annotated, Literal

from . import config
from .auth import build_auth_provider
from .services import ai_service, category_service, decision_service, storage
from .services.category_service import VataConflictError, VataNotFoundError

mcp = FastMCP("Vata", auth=build_auth_provider())


def _error(exc: Exception) -> dict:
    return {"error": str(exc), "error_type": type(exc).__name__}


# --- Tools: primary verbs ---


@mcp.tool
async def vata_save(
    content: Annotated[str, Field(description="A link (URL) or freeform text to save.")],
    title: Annotated[str | None, Field(description="Short title for this asset. You should decide this yourself from the content — don't leave it blank if you're a reasoning model.")] = None,
    category: Annotated[
        str | None,
        Field(description="Which category this belongs to. Call vata_list_categories first, pick an existing one that fits, or invent a short new one if none fit. You decide this — don't leave it blank if you're a reasoning model."),
    ] = None,
    category_description: Annotated[str | None, Field(description="One-sentence description of the category, only needed if `category` is a brand-new one that didn't already exist.")] = None,
    description: Annotated[
        str | None,
        Field(description="One-sentence description of the content itself, in your own words. You should write this yourself — don't leave it blank if you're a reasoning model."),
    ] = None,
    tags: Annotated[list[str] | None, Field(description="Up to 5 lowercase tags. You should pick these yourself — don't leave it blank if you're a reasoning model.")] = None,
) -> dict:
    """Save a link or note to Vata. Fill in title/category/description/tags
    yourself by reasoning about the content — call vata_list_categories
    first to see what already exists and reuse a fitting one, or invent a
    short new category name if nothing fits. Only leave these blank if you
    are not a reasoning model (e.g. a plain script); in that case the
    server falls back to VATA_LLM_MODEL or a local heuristic."""
    decision = await ai_service.decide_asset_metadata(
        content, description, tags, title, category, category_description
    )
    category_doc = category_service.resolve_or_create_category(
        decision["category"], decision.get("category_description", "")
    )
    result = category_service.add_asset_to_category_record(
        category_doc["_id"], decision["title"], content, decision["description"], decision["tags"]
    )
    return {
        "message": "Saved",
        "asset_id": result["asset_id"],
        "title": decision["title"],
        "category_id": category_doc["_id"],
        "category": category_doc["category"],
        "description": decision["description"],
        "tags": decision["tags"],
        "is_link": decision["is_link"],
    }


@mcp.tool
async def vata_list_categories() -> dict:
    """List every category with its name, AI-written description, and
    asset count. Present this as a table: Category | Description | Assets."""
    return category_service.list_categories_record()


@mcp.tool
async def vata_list_assets(
    category_id: Annotated[str | None, Field(description="Category to list assets from, by id.")] = None,
    category_name: Annotated[str | None, Field(description="Category to list assets from, by exact name (used if category_id omitted).")] = None,
) -> dict:
    """List every asset within one category. Present as a table: Title |
    Content (link/text) | Description | Tags."""
    try:
        return category_service.list_assets_in_category_record(category_id, category_name)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_find(
    query: Annotated[str, Field(description="Natural-language search query — what you're looking for.")],
) -> dict:
    """Search saved content by meaning. Ranks categories then assets via
    BM25, with an optional LLM re-rank pass for match reasons when an LLM
    is configured. Returns both the matching assets and the categories they
    came from — present both as tables."""
    return decision_service.evaluate_nodes_for_query(query)


@mcp.tool
async def vata_suggest(
    content: Annotated[str, Field(description="Content to preview AI filing decisions for, without saving.")],
    description: Annotated[str | None, Field(description="Optional hint about the content.")] = None,
    tags: Annotated[list[str] | None, Field(description="Optional tag override.")] = None,
) -> dict:
    """Preview what vata_save would decide (title/category/description/tags)
    without writing anything. Useful for transparency/debugging."""
    return await ai_service.fetch_suggestions(content, description, tags)


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
            "A personal link/notes archive exposed as MCP tools/prompts. Save "
            "a link or note with vata_save — the calling assistant is expected "
            "to reason about the content itself: call vata_list_categories "
            "first, pick a fitting existing category or invent a short new "
            "one, then pass explicit title/category/description/tags into "
            "vata_save. Anything left blank falls back to VATA_LLM_MODEL or a "
            "local heuristic. Retrieve by meaning with vata_find, or browse "
            "with vata_list_categories/vata_list_assets."
        ),
        "version": category_service.VATA_MCP_VERSION,
        "tools": sorted(t.name for t in tools),
        "prompts": sorted(p.name for p in prompts),
        "storage_backend": storage.backend_info(),
        "ai_backend": ai_service.backend_info(),
        "auth_enabled": bool(config.get("VATA_MCP_TOKEN")),
    }


# --- Tools: edit / delete (tool-only, no slash prompt except where noted) ---


@mcp.tool
async def vata_edit_category(
    category_id: Annotated[str | None, Field(description="Category to edit, by id.")] = None,
    current_name: Annotated[str | None, Field(description="Category to edit, by its current exact name (used if category_id omitted).")] = None,
    new_name: Annotated[str | None, Field(description="New name, if renaming.")] = None,
    description: Annotated[str | None, Field(description="New description. If omitted while renaming, AI should generate one and pass it here.")] = None,
) -> dict:
    """Edit a category's name and/or description. Provide the category by
    id or current_name, and at least one of new_name/description to change."""
    try:
        return category_service.edit_category_record(category_id, current_name, new_name, description)
    except (VataNotFoundError, VataConflictError) as e:
        return _error(e)


@mcp.tool
async def vata_edit_asset(
    asset_id: Annotated[str | None, Field(description="Asset to edit, by id.")] = None,
    current_title: Annotated[str | None, Field(description="Asset to edit, by its current exact title (used if asset_id omitted).")] = None,
    new_content: Annotated[str | None, Field(description="New link or text content, if changing.")] = None,
    new_title: Annotated[str | None, Field(description="New title, if new_content is given. You should decide this yourself by reasoning about new_content.")] = None,
    new_description: Annotated[str | None, Field(description="New one-sentence description, if new_content is given. You should write this yourself.")] = None,
    new_tags: Annotated[list[str] | None, Field(description="New tag list, if new_content is given. You should pick these yourself.")] = None,
    hint: Annotated[
        str | None,
        Field(description="Optional hint about the new content. Only used as a fallback if new_title/new_description/new_tags are left blank."),
    ] = None,
) -> dict:
    """Edit an existing asset. Look it up by asset_id or current_title. If
    new_content is given, decide new_title/new_description/new_tags
    yourself by reasoning about it — leave them blank only if you can't
    reason (falls back to VATA_LLM_MODEL or a local heuristic)."""
    try:
        if new_content is not None:
            decision = await ai_service.decide_asset_metadata(
                new_content, description=new_description or hint, tags=new_tags, title=new_title
            )
            return category_service.update_asset_record(
                asset_id,
                current_title,
                {
                    "title": decision["title"],
                    "content": new_content,
                    "description": decision["description"],
                    "tags": decision["tags"],
                },
            )
        return category_service.update_asset_record(asset_id, current_title, {})
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_delete_category(
    confirm: Annotated[Literal[True], Field(description="Must be explicitly true. Destructive — deletes the category AND every asset inside it.")],
    category_id: Annotated[str | None, Field(description="Category to delete, by id.")] = None,
    category_name: Annotated[str | None, Field(description="Category to delete, by exact name (used if category_id omitted).")] = None,
) -> dict:
    """Delete a category and every asset within it. Requires confirm=true."""
    try:
        return category_service.delete_category_record(category_id, category_name)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_delete_asset(
    confirm: Annotated[Literal[True], Field(description="Must be explicitly true. Destructive action.")],
    asset_id: Annotated[str | None, Field(description="Asset to delete, by id.")] = None,
    title: Annotated[str | None, Field(description="Asset to delete, by its exact title (used if asset_id omitted).")] = None,
) -> dict:
    """Delete a single asset (its category is unaffected). Requires
    confirm=true."""
    try:
        return category_service.delete_asset_record(asset_id, title)
    except VataNotFoundError as e:
        return _error(e)


@mcp.tool
async def vata_clean(
    password: Annotated[str, Field(description="Confirmation password. Must match the server's configured VATA_CLEAN_PASSWORD.")],
) -> dict:
    """Wipe the entire database: every category and every asset, gone.
    Requires the correct password — set via the VATA_CLEAN_PASSWORD env var
    on the server. Wrong password or the env var not being set at all both
    refuse the wipe."""
    expected = config.get("VATA_CLEAN_PASSWORD")
    if not expected:
        return _error(RuntimeError("vata_clean is disabled: VATA_CLEAN_PASSWORD is not set on the server"))
    if not hmac.compare_digest(password, expected):
        return _error(PermissionError("Incorrect password — database was not touched"))
    return category_service.wipe_all_data()


@mcp.tool
async def vata_replace_category(
    category_id: Annotated[str, Field(description="Category whose contents will be wholesale replaced.")],
    data: Annotated[
        dict,
        Field(description='Map of arbitrary keys to {"title"?, "content", "description"?, "tags"?} objects to become the new assets.'),
    ],
) -> dict:
    """Bulk-replace a category's assets: deletes everything currently in
    it, then creates new assets from `data`. Rarely used directly; kept for
    parity with bulk-import style flows."""
    try:
        return category_service.replace_category_record(category_id, data)
    except VataNotFoundError as e:
        return _error(e)


# --- Prompts: typed slash-command entry points ---


@mcp.prompt(name="vata-save")
def vata_save_prompt(content: str, description: str = "") -> str:
    """Save a link or note to Vata — you (the assistant) decide the title, category, description, and tags."""
    return (
        f"Save this to Vata: content={content!r}"
        + (f", with this hint from the user: {description!r}" if description else "")
        + ". First call vata_list_categories to see what categories already exist. "
        "Then decide yourself: a short title, which existing category this fits into "
        "(reuse one if it reasonably fits) or a short new category name if none fit, "
        "a one-sentence description of the content in your own words, and up to 5 "
        "lowercase tags. Call vata_save passing title/category/description/tags "
        "explicitly — don't leave them blank, you're the one deciding this, not the "
        "tool. Only pass category_description if you picked a brand-new category. "
        "Never ask the user which category to use — decide it yourself. Report back "
        "the title and category you chose."
    )


@mcp.prompt(name="vata-list-categories")
def vata_list_categories_prompt() -> str:
    """List all categories in a table: name, description, asset count."""
    return "Call the vata_list_categories tool and present the result as a table: Category | Description | Assets."


@mcp.prompt(name="vata-list-assets")
def vata_list_assets_prompt(category: str) -> str:
    """List all assets in a category, table: title, link/text, description, tags."""
    return (
        f"The user wants assets in category {category!r}. If this looks like a "
        "category_id, call vata_list_assets with category_id; otherwise call it "
        "with category_name. Present the result as a table: Title | Content | Description | Tags."
    )


@mcp.prompt(name="vata-find")
def vata_find_prompt(query: str) -> str:
    """Search everything saved to Vata by meaning."""
    return (
        f"Call the vata_find tool with query={query!r}. Present the results as two "
        "tables: one for matching assets (Title | Content | Description | Tags | Category | Match reason), "
        "and one for the categories they came from (Category | Description | Match count)."
    )


@mcp.prompt(name="vata-stats")
def vata_stats_prompt() -> str:
    """Show Vata's overall metrics: category count, asset count, version."""
    return "Call the vata_stats tool and report the category count, asset count, and version."


@mcp.prompt(name="vata-describe")
def vata_describe_prompt() -> str:
    """Describe what this Vata MCP server is and how it's configured."""
    return "Call the vata_describe tool and summarize what Vata is, its available tools/prompts, and its current storage/AI/auth configuration."


@mcp.prompt(name="vata-clean")
def vata_clean_prompt() -> str:
    """Wipe the entire database (all categories and assets). Destructive."""
    return (
        "The user wants to wipe the entire Vata database. Ask them for the clean "
        "password if they haven't given it yet, then call the vata_clean tool with "
        "that password. If it returns an error (wrong password, or the feature is "
        "disabled because VATA_CLEAN_PASSWORD isn't set on the server), report that "
        "clearly and do not retry silently."
    )


def main() -> None:
    transport = config.get("VATA_MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
    else:
        if not config.get("VATA_MCP_TOKEN"):
            print(
                "[vata-mcp] WARNING: VATA_MCP_TOKEN is not set — this HTTP server "
                "has NO auth and anyone with the URL can call every tool, "
                "including deletes. Set VATA_MCP_TOKEN before exposing this publicly."
            )
        host = config.get("VATA_MCP_HOST", "0.0.0.0")
        # Render/Railway/etc inject PORT (always a raw env var, not user config);
        # fall back to VATA_MCP_PORT for local runs.
        port = int(os.getenv("PORT") or config.get("VATA_MCP_PORT", "8765"))
        mcp.run(transport=transport, host=host, port=port)


if __name__ == "__main__":
    main()
