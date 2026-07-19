"""Category/asset CRUD. Each asset belongs to exactly one category
(`category_id` on the asset document) — no many-to-many join. Deleting a
category always deletes its assets. Raises `VataNotFoundError` /
`VataConflictError` instead of FastAPI's HTTPException, since this is a
standalone MCP server with no web framework underneath.
"""

from importlib.metadata import PackageNotFoundError, version

from . import storage

try:
    VATA_MCP_VERSION = version("vata-mcp")
except PackageNotFoundError:
    VATA_MCP_VERSION = "0.0.0-dev"


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


def resolve_asset(asset_id: str | None, title: str | None) -> dict:
    """Look up an asset by id first, then by title (case-insensitive exact
    match). At least one of asset_id/title must be given."""
    if asset_id:
        asset = storage.get_asset(asset_id)
        if asset:
            return asset
        raise VataNotFoundError(f"Asset not found: {asset_id}")
    if title:
        asset = storage.find_asset_by_title(title)
        if asset:
            return asset
        raise VataNotFoundError(f"No asset found with title: {title!r}")
    raise VataNotFoundError("Must provide asset_id or title")


def resolve_category(category_id: str | None, name: str | None) -> dict:
    """Look up a category by id first, then by exact name."""
    if category_id:
        cat = storage.get_category(category_id)
        if cat:
            return cat
        raise VataNotFoundError(f"Category not found: {category_id}")
    if name:
        cat = storage.find_category_by_name(name)
        if cat:
            return cat
        raise VataNotFoundError(f"No category found with name: {name!r}")
    raise VataNotFoundError("Must provide category_id or name")


def _asset_row(asset: dict) -> dict:
    return {
        "asset_id": asset["_id"],
        "title": asset.get("title", ""),
        "content": asset.get("content", ""),
        "description": asset.get("description", ""),
        "tags": asset.get("tags", []),
        "category_id": asset.get("category_id", ""),
        "created_at": asset.get("created_at", ""),
        "updated_at": asset.get("updated_at", ""),
    }


# --- Categories ---


def resolve_or_create_category(name: str, description: str = "") -> dict:
    """Find an existing category by exact name, else create one. `description`
    is only used when the category is new — existing categories keep theirs."""
    existing = storage.find_category_by_name(name)
    if existing:
        return existing
    category_id = storage.new_category_id(name)
    return storage.insert_category(category_id, name, description)


def create_category_record(category: str, description: str = "") -> dict:
    if not category:
        raise ValueError("Category cannot be empty")
    category_id = storage.new_category_id(category)
    doc = storage.insert_category(category_id, category, description)
    return {"message": "Category created", "category_id": category_id, "category": doc["category"]}


def list_categories_record() -> dict:
    """Table-style listing: name, description, and asset count per category."""
    rows = []
    for c in storage.list_categories():
        rows.append({
            "category_id": c["_id"],
            "category": c["category"],
            "description": c.get("description", ""),
            "asset_count": storage.count_assets_in_category(c["_id"]),
        })
    return {"count": len(rows), "categories": rows}


def list_assets_in_category_record(category_id: str | None = None, category_name: str | None = None) -> dict:
    """Table-style listing of every asset in one category: title, content
    (link/text), description, tags."""
    cat = resolve_category(category_id, category_name)
    assets = storage.list_assets_in_category(cat["_id"])
    rows = [
        {
            "asset_id": a["_id"],
            "title": a.get("title", ""),
            "content": a.get("content", ""),
            "description": a.get("description", ""),
            "tags": a.get("tags", []),
        }
        for a in assets
    ]
    return {
        "category": cat["category"],
        "category_id": cat["_id"],
        "count": len(rows),
        "assets": rows,
    }


def edit_category_record(
    category_id: str | None,
    current_name: str | None,
    new_name: str | None = None,
    description: str | None = None,
) -> dict:
    """Edit a category's name and/or description. Renaming changes the
    category_id (IDs are name+timestamp derived); assets are moved to the
    new id automatically."""
    cat = resolve_category(category_id, current_name)
    result_id = cat["_id"]

    if new_name and new_name != cat["category"]:
        new_id = storage.new_category_id(new_name)
        if storage.get_category(new_id):
            raise VataConflictError("Target category id already exists")
        storage.rename_category(cat["_id"], new_id, new_name)
        result_id = new_id

    if description is not None:
        storage.update_category_fields(result_id, {"description": description})

    updated = storage.get_category(result_id)
    return {
        "message": "Category updated",
        "category_id": result_id,
        "category": updated["category"],
        "description": updated.get("description", ""),
    }


def delete_category_record(category_id: str | None = None, category_name: str | None = None) -> dict:
    """Delete a category and every asset within it."""
    cat = resolve_category(category_id, category_name)
    deleted_asset_ids = storage.delete_assets_in_category(cat["_id"])
    storage.delete_category(cat["_id"])
    return {
        "message": "Category and all its assets deleted",
        "category_id": cat["_id"],
        "deleted_asset_ids": deleted_asset_ids,
        "deleted_asset_count": len(deleted_asset_ids),
    }


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
    """Bulk-replace: delete all current assets in the category, create new
    ones from `data` (each value needs at least "content")."""
    _require_category(category_id)
    storage.delete_assets_in_category(category_id)

    written = {}
    for asset_data in (data or {}).values():
        asset_id = storage.new_asset_id()
        doc = storage.insert_asset(
            asset_id,
            category_id,
            asset_data.get("title", ""),
            asset_data.get("content", ""),
            asset_data.get("description", ""),
            asset_data.get("tags", []),
        )
        written[asset_id] = doc

    storage.touch_category(category_id)
    return {"message": "Category replaced", "category_id": category_id, "data": written}


# --- Assets ---


def add_asset_to_category_record(
    category_id: str, title: str, content: str, description: str | None = None, tags: list[str] | None = None
) -> dict:
    _require_category(category_id)
    asset_id = storage.new_asset_id()
    storage.insert_asset(asset_id, category_id, title, content, description or "", tags or [])
    storage.touch_category(category_id)
    return {"message": "Asset added", "category_id": category_id, "asset_id": asset_id}


def get_asset_record(asset_id: str | None = None, title: str | None = None) -> dict:
    asset = resolve_asset(asset_id, title)
    return _asset_row(asset)


def update_asset_record(asset_id: str | None, title: str | None, fields: dict) -> dict:
    asset = resolve_asset(asset_id, title)
    storage.update_asset(asset["_id"], fields)
    storage.touch_category(asset["category_id"])
    return get_asset_record(asset_id=asset["_id"])


def delete_asset_record(asset_id: str | None = None, title: str | None = None) -> dict:
    asset = resolve_asset(asset_id, title)
    storage.delete_asset(asset["_id"])
    storage.touch_category(asset["category_id"])
    return {"message": "Asset deleted", "asset_id": asset["_id"], "title": asset.get("title", "")}


def get_stats() -> dict:
    return {
        "categories": storage.count_categories(),
        "assets": storage.count_assets(),
        "version": VATA_MCP_VERSION,
    }


def wipe_all_data() -> dict:
    result = storage.wipe_all()
    return {"message": "All categories and assets deleted", **result}
