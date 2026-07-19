"""End-to-end smoke test against the underlying services (bypasses the MCP
transport layer, calls the same async functions the tools call). Runs
entirely against the in-memory mongomock dummy DB + heuristic AI — no
external services required.

Run: python scripts/smoke_test.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from vata_mcp.services import ai_service, category_service, decision_service


def check(label: str, condition: bool, detail: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" — {detail}" if detail and not condition else ""))
    if not condition:
        raise SystemExit(1)


async def main() -> None:
    print("=== vata-mcp smoke test ===\n")

    # 1. Save two clearly different pieces of content -> expect two categories
    decision1 = await ai_service.decide_category_and_metadata(
        "Recipe for tomato basil pasta: boil pasta, saute garlic and basil, add crushed tomatoes, simmer 10 minutes."
    )
    cat1 = category_service.resolve_or_create_category(decision1["category"])
    save1 = category_service.add_asset_to_category_record(cat1["_id"], "Recipe for tomato basil pasta...", decision1["summary"], decision1["tags"])
    check("vata_save #1 created an asset", bool(save1.get("asset_id")))
    print(f"  -> filed under category: {cat1['category']!r} (id={cat1['_id']})")

    decision2 = await ai_service.decide_category_and_metadata(
        "Quarterly budget review meeting notes: Q3 revenue up 12%, marketing spend needs review, follow up with finance team next week."
    )
    cat2 = category_service.resolve_or_create_category(decision2["category"])
    save2 = category_service.add_asset_to_category_record(cat2["_id"], "Quarterly budget review meeting notes...", decision2["summary"], decision2["tags"])
    check("vata_save #2 created an asset", bool(save2.get("asset_id")))
    print(f"  -> filed under category: {cat2['category']!r} (id={cat2['_id']})")

    check("Two different topics landed in two different categories", cat1["_id"] != cat2["_id"])

    # 2. Save a third, similar-to-#1 note -> should reuse category 1 (heuristic-dependent, so just report)
    decision3 = await ai_service.decide_category_and_metadata(
        "Another pasta recipe: penne with garlic and olive oil, add basil and parmesan."
    )
    cat3 = category_service.resolve_or_create_category(decision3["category"])
    save3 = category_service.add_asset_to_category_record(cat3["_id"], "Another pasta recipe...", decision3["summary"], decision3["tags"])
    check("vata_save #3 created an asset", bool(save3.get("asset_id")))
    print(f"  -> filed under category: {cat3['category']!r} (id={cat3['_id']}) [expected to reuse #1's category ideally]")

    # 3. vata_get: list categories
    listing = category_service.list_categories_record()
    check("vata_get (list categories) returns at least 2 categories", len(listing["categories"]) >= 2, str(listing))

    # 4. vata_get: category summary
    summary = category_service.get_category_summary(cat1["_id"])
    check("vata_get (category summary) returns items", summary["count"] >= 1, str(summary))

    # 5. vata_get: full asset
    full = category_service.get_asset_record(save1["asset_id"])
    check("vata_get (asset) returns main_content", "pasta" in full["main_content"].lower())

    # 6. vata_find: search by meaning
    find_result = decision_service.evaluate_nodes_for_query("pasta recipe with basil")
    check("vata_find returns at least one result for 'pasta recipe with basil'", find_result["count"] >= 1, str(find_result))
    found_ids = {r["asset_id"] for r in find_result["data"]}
    check("vata_find surfaces the pasta asset among results", save1["asset_id"] in found_ids or save3["asset_id"] in found_ids)

    find_budget = decision_service.evaluate_nodes_for_query("budget meeting finance")
    check("vata_find returns results for 'budget meeting finance'", find_budget["count"] >= 1, str(find_budget))

    # 7. vata_edit_asset
    edit_result = category_service.update_asset_in_record(cat1["_id"], save1["asset_id"], {"summary": "Edited summary for pasta recipe", "main_content": None, "tags": None})
    check("vata_edit_asset succeeds", edit_result.get("message") == "Asset updated")
    edited = category_service.get_asset_record(save1["asset_id"])
    check("Edit persisted", edited["summary"] == "Edited summary for pasta recipe", edited["summary"])

    # 8. vata_link_asset / vata_unlink_asset
    link_result = category_service.link_asset_to_category(cat2["_id"], save1["asset_id"])
    check("vata_link_asset attaches asset to a second category", cat2["_id"] in link_result["categories"])

    unlink_result = category_service.unlink_asset_from_category(cat2["_id"], save1["asset_id"])
    check("vata_unlink_asset detaches without deleting (still in cat1)", not unlink_result["deleted"] and cat1["_id"] in unlink_result["categories"])

    # 9. vata_rename_category
    rename_result = category_service.rename_category_record(cat3["_id"], "Pasta Recipes Renamed")
    check("vata_rename_category succeeds", rename_result["old_id"] == cat3["_id"])
    renamed_cat_id = rename_result["new_id"]
    check("Renamed category is retrievable under new id", category_service.get_category_summary(renamed_cat_id)["category"] == "Pasta Recipes Renamed")

    # 10. vata_delete_asset -> unlink from last category -> hard delete
    delete_result = category_service.delete_asset_from_record(renamed_cat_id, save3["asset_id"])
    check("vata_delete_asset hard-deletes when orphaned", delete_result["hard_deleted"] is True)
    try:
        category_service.get_asset_record(save3["asset_id"])
        check("Deleted asset should no longer be retrievable", False)
    except category_service.VataNotFoundError:
        check("Deleted asset correctly raises not-found", True)

    # 11. vata_delete_category
    delete_cat_result = category_service.delete_category_record(cat2["_id"])
    check("vata_delete_category succeeds", delete_cat_result["category_id"] == cat2["_id"])
    try:
        category_service.get_category_summary(cat2["_id"])
        check("Deleted category should no longer be retrievable", False)
    except category_service.VataNotFoundError:
        check("Deleted category correctly raises not-found", True)

    # 12. vata_suggest (preview only, no save)
    preview = await ai_service.fetch_suggestions("A note about hiking trails in the mountains near the cabin.")
    check("vata_suggest returns a category/summary/tags shape", all(k in preview for k in ("category", "summary", "tags")), str(preview))

    print("\n=== All smoke tests passed ===")


if __name__ == "__main__":
    asyncio.run(main())
