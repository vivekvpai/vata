"""Category/asset CRUD + many-to-many membership. Ported from the original
vata `category_service.py`, adapted to the Mongo storage layer. Raises
`VataNotFoundError` / `VataConflictError` instead of FastAPI's
HTTPException, since this is a standalone MCP server with no web framework
underneath.
"""

from . import storage


class VataNotFoundError(Exception):
    pass


class VataConflictError(Exception):
    pass


def _require_category(category_id: str) -> dict:
    cat = storage.get_category(category_id)
    if not cat:
        raise VataNotFoundError(f"Category not found: {category_id}")
    return cat


def _require_asset(asset_id: str) -> dict:
    asset = storage.get_asset(asset_id)
    if not asset:
        raise VataNotFoundError(f"Asset not found: {asset_id}")
    return asset


def _summary_entry(asset_id: str, asset: dict) -> dict:
    return {
        "asset_id": asset_id,
        "summary": asset.get("summary", ""),
        "tags": asset.get("tags", []),
        "content_snippet": (asset.get("main_content", "") or "")[:200],
        "updated_at": asset.get("updated_at", ""),
        "categories": storage.categories_for_asset(asset_id),
    }


# --- Categories ---


def resolve_or_create_category(name: str) -> dict:
    """Find an existing category by exact name, else create one."""
    existing = storage.find_category_by_name(name)
    if existing:
        return existing
    category_id = storage.new_category_id(name)
    return storage.insert_category(category_id, name)


def create_category_record(category: str) -> dict:
    if not category:
        raise ValueError("Category cannot be empty")
    category_id = storage.new_category_id(category)
    doc = storage.insert_category(category_id, category)
    return {"message": "Category created", "category_id": category_id, "category": doc["category"]}


def list_categories_record() -> dict:
    return {"categories": [{"category_id": c["_id"], "category": c["category"]} for c in storage.list_categories()]}


def get_category_summary(category_id: str) -> dict:
    cat = _require_category(category_id)
    items = []
    for aid in storage.members_of_category(category_id):
        asset = storage.get_asset(aid)
        if asset:
            items.append(_summary_entry(aid, asset))
    return {"category": cat["category"], "category_id": category_id, "count": len(items), "items": items}


def delete_category_record(category_id: str) -> dict:
    _require_category(category_id)
    member_ids = storage.remove_all_members_of_category(category_id)
    storage.delete_category(category_id)

    orphaned = []
    for aid in member_ids:
        if not storage.categories_for_asset(aid):
            storage.delete_asset(aid)
            orphaned.append(aid)

    return {"message": "Category deleted", "category_id": category_id, "orphaned_assets_deleted": orphaned}


def rename_category_record(category_id: str, new_name: str) -> dict:
    _require_category(category_id)
    if not new_name:
        raise ValueError("New name cannot be empty")
    new_id = storage.new_category_id(new_name)
    if storage.get_category(new_id):
        raise VataConflictError("Target category id already exists")
    storage.rename_category(category_id, new_id, new_name)
    return {"message": "Category renamed", "old_id": category_id, "new_id": new_id}


def replace_category_record(category_id: str, data: dict) -> dict:
    """Bulk-replace: unlink all current members, create new assets from `data`."""
    _require_category(category_id)
    for aid in list(storage.members_of_category(category_id)):
        unlink_asset_from_category(category_id, aid)

    written = {}
    for asset_data in (data or {}).values():
        result = add_asset_to_category_record(
            category_id,
            asset_data.get("main_content", ""),
            asset_data.get("summary"),
            asset_data.get("tags"),
        )
        written[result["asset_id"]] = storage.get_asset(result["asset_id"])

    storage.touch_category(category_id)
    return {"message": "Category replaced", "category_id": category_id, "data": written}


# --- Assets ---


def add_asset_to_category_record(
    category_id: str, main_content: str, summary: str | None = None, tags: list[str] | None = None
) -> dict:
    _require_category(category_id)
    asset_id = storage.new_asset_id()
    storage.insert_asset(asset_id, main_content, summary or "", tags or [])
    storage.add_member(category_id, asset_id)
    storage.touch_category(category_id)
    return {"message": "Asset added", "category_id": category_id, "asset_id": asset_id}


def get_asset_record(asset_id: str) -> dict:
    asset = _require_asset(asset_id)
    return {
        "asset_id": asset_id,
        "main_content": asset.get("main_content", ""),
        "summary": asset.get("summary", ""),
        "tags": asset.get("tags", []),
        "categories": storage.categories_for_asset(asset_id),
        "created_at": asset.get("created_at"),
        "updated_at": asset.get("updated_at"),
    }


def update_asset_in_record(category_id: str, asset_id: str, fields: dict) -> dict:
    _require_category(category_id)
    _require_asset(asset_id)
    if category_id not in storage.categories_for_asset(asset_id):
        raise VataNotFoundError("Asset not in this category")
    storage.update_asset(asset_id, fields)
    storage.touch_category(category_id)
    return {"message": "Asset updated", "category_id": category_id, "asset_id": asset_id}


def delete_asset_from_record(category_id: str, asset_id: str) -> dict:
    """Unlink from this category. If asset has no other categories, hard-delete it."""
    _require_category(category_id)
    _require_asset(asset_id)
    if category_id not in storage.categories_for_asset(asset_id):
        raise VataNotFoundError("Asset not in this category")

    result = unlink_asset_from_category(category_id, asset_id)
    storage.touch_category(category_id)
    return {
        "message": "Asset deleted",
        "category_id": category_id,
        "asset_id": asset_id,
        "hard_deleted": result["deleted"],
    }


# --- Many-to-many ---


def link_asset_to_category(category_id: str, asset_id: str) -> dict:
    _require_category(category_id)
    _require_asset(asset_id)
    storage.add_member(category_id, asset_id)
    storage.touch_category(category_id)
    return {
        "message": "Asset linked",
        "category_id": category_id,
        "asset_id": asset_id,
        "categories": storage.categories_for_asset(asset_id),
    }


def unlink_asset_from_category(category_id: str, asset_id: str) -> dict:
    _require_category(category_id)
    _require_asset(asset_id)
    storage.remove_member(category_id, asset_id)

    remaining = storage.categories_for_asset(asset_id)
    deleted = False
    if not remaining:
        storage.delete_asset(asset_id)
        deleted = True

    return {
        "message": "Asset unlinked",
        "category_id": category_id,
        "asset_id": asset_id,
        "categories": remaining,
        "deleted": deleted,
    }
