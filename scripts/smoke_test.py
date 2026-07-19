"""End-to-end smoke test against the underlying services (bypasses the MCP
transport layer for most calls, but exercises vata_describe/vata_clean
through a real MCP client). Runs entirely against the in-memory mongomock
dummy DB + heuristic AI by default — no external services required.

Model: each asset belongs to exactly one category. vata_save takes a
link/text `content` plus an optional `description` hint; AI generates the
title, category, content description, and tags.

WARNING: this test calls vata_clean, which wipes the entire database it's
pointed at. If VATA_MONGODB_URI is already set in your environment when you
run this, it WILL wipe that real database. To force running against a real
DB anyway, pass --allow-real-db explicitly.

Run: python scripts/smoke_test.py
"""

import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

if "--allow-real-db" not in sys.argv and os.getenv("VATA_MONGODB_URI"):
    print(
        "[smoke_test] Refusing to run: VATA_MONGODB_URI is set and this test "
        "calls vata_clean, which would wipe that real database.\n"
        "[smoke_test] Unset VATA_MONGODB_URI to run against the safe in-memory "
        "dummy DB, or re-run with --allow-real-db if you really mean to wipe it."
    )
    sys.exit(1)

from fastmcp import Client

from vata_mcp.server import mcp
from vata_mcp.services import ai_service, category_service, decision_service


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        raise SystemExit(1)


async def _save(content: str, description: str | None = None) -> tuple[dict, dict]:
    """Mirrors the vata_save tool's logic against the service layer directly."""
    decision = await ai_service.decide_asset_metadata(content, description)
    cat = category_service.resolve_or_create_category(decision["category"], decision["category_description"])
    result = category_service.add_asset_to_category_record(
        cat["_id"], decision["title"], content, decision["description"], decision["tags"]
    )
    return decision, {**result, "category_id": cat["_id"], "category": cat["category"], "title": decision["title"]}


async def main() -> None:
    print("=== vata-mcp smoke test ===\n")

    # 1. Save a link with a description hint
    decision1, save1 = await _save(
        "https://docs.python.org/3/library/asyncio.html",
        "python asyncio reference docs, useful for async patterns",
    )
    check("vata_save #1 decision has title/category/description/tags", all(k in decision1 for k in ("title", "category", "description", "tags")), str(decision1))
    check("vata_save #1 detected this as a link", decision1["is_link"] is True, str(decision1))
    check("vata_save #1 created an asset", bool(save1.get("asset_id")))
    print(f"  -> title={save1['title']!r} category={save1['category']!r} (id={save1['category_id']})")

    # 2. Save plain text, unrelated topic -> expect a different category
    decision2, save2 = await _save(
        "Quarterly budget review meeting notes: Q3 revenue up 12%, marketing spend needs review.",
    )
    check("vata_save #2 detected this as text, not a link", decision2["is_link"] is False, str(decision2))
    check("vata_save #2 created an asset", bool(save2.get("asset_id")))
    check("Two different topics landed in two different categories", save1["category_id"] != save2["category_id"])
    print(f"  -> title={save2['title']!r} category={save2['category']!r}")

    # 3. Save a second link related to #1 -> should ideally reuse its category (heuristic-dependent)
    decision3, save3 = await _save(
        "https://docs.python.org/3/library/concurrent.futures.html",
        "python concurrency docs, related to asyncio",
    )
    check("vata_save #3 created an asset", bool(save3.get("asset_id")))
    print(f"  -> title={save3['title']!r} category={save3['category']!r} [expected to reuse #1's category ideally]")

    # 4. vata_list_categories: table view
    listing = category_service.list_categories_record()
    check("vata_list_categories returns at least 2 categories", len(listing["categories"]) >= 2, str(listing))
    check("vata_list_categories rows include description and asset_count", all("description" in row and "asset_count" in row for row in listing["categories"]), str(listing))

    # 5. vata_list_assets: table view for category #1
    assets_in_cat1 = category_service.list_assets_in_category_record(category_id=save1["category_id"])
    check("vata_list_assets returns at least 1 asset for category #1", assets_in_cat1["count"] >= 1, str(assets_in_cat1))
    check("vata_list_assets rows include title/content/description/tags", all(
        all(k in row for k in ("title", "content", "description", "tags")) for row in assets_in_cat1["assets"]
    ), str(assets_in_cat1))

    # 5b. vata_list_assets by category_name instead of id
    assets_by_name = category_service.list_assets_in_category_record(category_name=save1["category"])
    check("vata_list_assets works by category_name too", assets_by_name["category_id"] == save1["category_id"], str(assets_by_name))

    # 6. vata_edit_category: rename + description in one call
    edit_cat_result = category_service.edit_category_record(
        category_id=save1["category_id"], current_name=None, new_name="Async Python Docs", description="Reference docs about Python async/concurrency."
    )
    check("vata_edit_category succeeds", edit_cat_result.get("message") == "Category updated", str(edit_cat_result))
    check("vata_edit_category applied the new name", edit_cat_result["category"] == "Async Python Docs", str(edit_cat_result))
    new_cat1_id = edit_cat_result["category_id"]
    check("vata_edit_category changed the category_id on rename", new_cat1_id != save1["category_id"])

    moved_assets = category_service.list_assets_in_category_record(category_id=new_cat1_id)
    check("Assets moved along with the renamed category", moved_assets["count"] >= 1, str(moved_assets))

    # 6b. vata_edit_category: description-only edit, no rename
    edit_cat_result2 = category_service.edit_category_record(category_id=new_cat1_id, current_name=None, description="Updated description only.")
    check("vata_edit_category (description-only) keeps the same id", edit_cat_result2["category_id"] == new_cat1_id, str(edit_cat_result2))
    check("vata_edit_category (description-only) applied", edit_cat_result2["description"] == "Updated description only.", str(edit_cat_result2))

    # 7. vata_get equivalent: fetch a single asset by id, then by title
    full = category_service.get_asset_record(asset_id=save1["asset_id"])
    check("get_asset_record by id returns content", "asyncio" in full["content"].lower())
    full_by_title = category_service.get_asset_record(title=save1["title"])
    check("get_asset_record by title resolves the same asset", full_by_title["asset_id"] == save1["asset_id"], str(full_by_title))

    # 8. vata_find: search by meaning, expect both assets + categories tables
    find_result = decision_service.evaluate_nodes_for_query("python asyncio concurrency documentation")
    check("vata_find returns at least one asset result", find_result["count"] >= 1, str(find_result))
    check("vata_find returns a categories table too", "categories" in find_result and len(find_result["categories"]) >= 1, str(find_result))
    found_ids = {r["asset_id"] for r in find_result["assets"]}
    check("vata_find surfaces one of the asyncio assets among results", save1["asset_id"] in found_ids or save3["asset_id"] in found_ids)

    find_budget = decision_service.evaluate_nodes_for_query("budget meeting finance")
    check("vata_find returns results for 'budget meeting finance'", find_budget["count"] >= 1, str(find_budget))

    # 9. vata_edit_asset: regenerate title/description/tags from new content
    new_decision = await ai_service.decide_asset_metadata(
        "https://docs.python.org/3/library/asyncio.html", "updated: now the canonical asyncio reference"
    )
    edit_result = category_service.update_asset_record(
        save1["asset_id"], None,
        {"title": new_decision["title"], "content": "https://docs.python.org/3/library/asyncio.html", "description": new_decision["description"], "tags": new_decision["tags"]},
    )
    check("vata_edit_asset succeeds", edit_result["asset_id"] == save1["asset_id"], str(edit_result))
    check("Edit persisted new description", edit_result["description"] == new_decision["description"], edit_result["description"])

    # 10. vata_delete_asset: removes only that asset, category survives
    delete_result = category_service.delete_asset_record(asset_id=save3["asset_id"])
    check("vata_delete_asset succeeds", delete_result["asset_id"] == save3["asset_id"], str(delete_result))
    try:
        category_service.get_asset_record(asset_id=save3["asset_id"])
        check("Deleted asset should no longer be retrievable", False)
    except category_service.VataNotFoundError:
        check("Deleted asset correctly raises not-found", True)
    check("Category #1 still exists after deleting one of its assets", category_service.list_assets_in_category_record(category_id=new_cat1_id)["count"] >= 1)

    # 11. vata_delete_category: cascades to remaining assets in it
    delete_cat_result = category_service.delete_category_record(category_id=save2["category_id"])
    check("vata_delete_category succeeds", delete_cat_result["category_id"] == save2["category_id"], str(delete_cat_result))
    check("vata_delete_category deleted its asset too", save2["asset_id"] in delete_cat_result["deleted_asset_ids"], str(delete_cat_result))
    try:
        category_service.get_asset_record(asset_id=save2["asset_id"])
        check("Cascaded-deleted asset should no longer be retrievable", False)
    except category_service.VataNotFoundError:
        check("Cascaded-deleted asset correctly raises not-found", True)

    # 12. vata_suggest (preview only, no save)
    preview = await ai_service.fetch_suggestions("https://example.com/some-article", "an interesting article")
    check("vata_suggest returns title/category/description/tags/is_link shape", all(k in preview for k in ("title", "category", "description", "tags", "is_link")), str(preview))

    # 12b. vata_save via the real MCP tool with everything explicit — the caller (a reasoning
    # LLM in real use) decides title/category/description/tags; the server must pass them
    # through untouched, not overwrite them with its own heuristic/LLM guess.
    async with Client(mcp) as client:
        explicit_save = (await client.call_tool("vata_save", {
            "content": "https://fastapi.tiangolo.com/tutorial/",
            "title": "FastAPI official tutorial",
            "category": "Web Frameworks",
            "category_description": "Docs and links about Python web frameworks.",
            "description": "Official step-by-step tutorial for building APIs with FastAPI.",
            "tags": ["fastapi", "python", "tutorial", "web"],
        })).data
    check("vata_save preserves an explicit caller-provided title verbatim", explicit_save["title"] == "FastAPI official tutorial", str(explicit_save))
    check("vata_save preserves an explicit caller-provided category verbatim", explicit_save["category"] == "Web Frameworks", str(explicit_save))
    check("vata_save preserves an explicit caller-provided description verbatim", explicit_save["description"] == "Official step-by-step tutorial for building APIs with FastAPI.", str(explicit_save))
    check("vata_save preserves explicit caller-provided tags verbatim", explicit_save["tags"] == ["fastapi", "python", "tutorial", "web"], str(explicit_save))

    # 12c. vata_save with only title+category given — description/tags should still be filled by the fallback
    async with Client(mcp) as client:
        partial_save = (await client.call_tool("vata_save", {
            "content": "https://docs.python.org/3/",
            "title": "Python official docs",
            "category": "Web Frameworks",
        })).data
    check("vata_save preserves partial explicit title", partial_save["title"] == "Python official docs", str(partial_save))
    check("vata_save preserves partial explicit category", partial_save["category"] == "Web Frameworks", str(partial_save))
    check("vata_save fills in a description when left blank", bool(partial_save["description"]), str(partial_save))
    check("vata_save fills in tags when left blank", len(partial_save["tags"]) > 0, str(partial_save))

    # 13. vata_stats: metrics
    stats = category_service.get_stats()
    check("vata_stats returns categories/assets/version", all(k in stats for k in ("categories", "assets", "version")), str(stats))
    print(f"  -> stats: {stats}")

    # 14. vata_describe (server-level introspection — via a real MCP client)
    async with Client(mcp) as client:
        describe_result = (await client.call_tool("vata_describe", {})).data
    check(
        "vata_describe returns name/tools/prompts/backends",
        all(k in describe_result for k in ("name", "tools", "prompts", "storage_backend", "ai_backend", "auth_enabled")),
        str(describe_result),
    )
    check("vata_describe lists vata_save among tools", "vata_save" in describe_result["tools"], str(describe_result["tools"]))
    check("vata_describe lists vata-find among prompts", "vata-find" in describe_result["prompts"], str(describe_result["prompts"]))
    print(f"  -> describe: {describe_result['storage_backend']}, {describe_result['ai_backend']}, auth_enabled={describe_result['auth_enabled']}")

    # 15. vata_clean: disabled without VATA_CLEAN_PASSWORD, wrong password refused, correct password wipes everything
    async with Client(mcp) as client:
        disabled_result = (await client.call_tool("vata_clean", {"password": "anything"})).data
    check("vata_clean is disabled when VATA_CLEAN_PASSWORD is unset", disabled_result.get("error_type") == "RuntimeError", str(disabled_result))

    os.environ["VATA_CLEAN_PASSWORD"] = "vata-smoke-test-password"
    async with Client(mcp) as client:
        wrong_pw_result = (await client.call_tool("vata_clean", {"password": "wrong-one"})).data
    check("vata_clean refuses a wrong password", wrong_pw_result.get("error_type") == "PermissionError", str(wrong_pw_result))
    check("vata_clean did not touch data on wrong password", category_service.get_stats()["assets"] > 0, str(category_service.get_stats()))

    async with Client(mcp) as client:
        clean_result = (await client.call_tool("vata_clean", {"password": "vata-smoke-test-password"})).data
    check("vata_clean succeeds with the correct password", clean_result.get("message") == "All categories and assets deleted", str(clean_result))
    final_stats = category_service.get_stats()
    check("vata_clean wiped everything", final_stats["categories"] == 0 and final_stats["assets"] == 0, str(final_stats))
    del os.environ["VATA_CLEAN_PASSWORD"]

    print("\n=== All smoke tests passed ===")


if __name__ == "__main__":
    asyncio.run(main())
