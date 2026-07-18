import shutil

from fastapi import HTTPException

from . import storage


def ensure_data_dir() -> None:
    storage.ensure_data_dir()
    storage.rebuild_index()


# --- Internal helpers ---


def _require_category(category_id: str) -> None:
    if not storage.category_dir(category_id).is_dir():
        raise HTTPException(status_code=404, detail="Category not found")


def _require_asset(asset_id: str) -> None:
    if not storage.asset_path(asset_id).exists():
        raise HTTPException(status_code=404, detail="Asset not found")


def _read_meta(category_id: str) -> dict:
    return storage.read_json(storage.meta_path(category_id))


def _write_meta(category_id: str, meta: dict) -> None:
    storage.write_json_atomic(storage.meta_path(category_id), meta)


def _bump_meta_updated(category_id: str) -> None:
    meta = _read_meta(category_id)
    meta["updated_at"] = storage.now_iso()
    _write_meta(category_id, meta)


def _read_asset(asset_id: str) -> dict:
    return storage.read_json(storage.asset_path(asset_id))


def _write_asset(asset_id: str, payload: dict) -> None:
    storage.write_json_atomic(storage.asset_path(asset_id), payload)


def _asset_categories(asset_id: str) -> list[str]:
    cats = []
    for cid in storage.list_category_ids():
        if asset_id in storage.read_members(cid):
            cats.append(cid)
    return cats


def _add_member(category_id: str, asset_id: str) -> None:
    members = storage.read_members(category_id)
    if asset_id not in members:
        members.append(asset_id)
        storage.write_members(category_id, members)


def _remove_member(category_id: str, asset_id: str) -> None:
    members = storage.read_members(category_id)
    if asset_id in members:
        members = [m for m in members if m != asset_id]
        storage.write_members(category_id, members)


# --- Categories ---


def create_category_record(category: str, data: dict | None = None) -> dict:
    if not category:
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    category_id = storage.new_category_id(category)
    storage.ensure_category_dir(category_id)

    now = storage.now_iso()
    _write_meta(category_id, {
        "category": category,
        "category_id": category_id,
        "created_at": now,
        "updated_at": now,
    })
    storage.write_members(category_id, [])

    if data:
        for asset in data.values():
            add_asset_to_category_record(category_id, asset)

    return {
        "message": "Category file created",
        "category_id": category_id,
        "filename": "meta.json",
    }


def list_categories_record() -> dict:
    return {cid: None for cid in storage.list_category_ids()}


def get_category_record(category: str) -> dict:
    _require_category(category)
    meta = _read_meta(category)

    assets: dict[str, dict] = {}
    for aid in storage.read_members(category):
        path = storage.asset_path(aid)
        if path.exists():
            assets[aid] = storage.read_json(path)

    return {
        "category": meta.get("category", category),
        "filename": "meta.json",
        "content": {
            "category": meta.get("category", category),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
            "data": assets,
        },
    }


def get_category_summary(category: str) -> dict:
    """Fast listing — pulls from index.json, no per-asset reads."""
    _require_category(category)
    meta = _read_meta(category)
    index = storage.load_index()

    items = []
    for aid in storage.read_members(category):
        entry = index.get(aid)
        if not entry:
            continue
        items.append({
            "asset_id": aid,
            "summary": entry.get("summary", ""),
            "tags": entry.get("tags", []),
            "content_snippet": entry.get("content_snippet", ""),
            "updated_at": entry.get("updated_at", ""),
            "categories": entry.get("categories", []),
        })

    return {
        "category": meta.get("category", category),
        "category_id": category,
        "count": len(items),
        "items": items,
    }


def update_category_record(category: str, data: dict) -> dict:
    """Replace this category's membership wholesale.
    Asset values in `data` are treated as new assets to create. Existing
    members are unlinked (assets remain in the global store unless orphaned)."""
    _require_category(category)

    for aid in list(storage.read_members(category)):
        unlink_asset_from_category(category, aid)

    written: dict[str, dict] = {}
    for asset in (data or {}).values():
        result = add_asset_to_category_record(category, asset)
        aid = result["asset_id"]
        written[aid] = _read_asset(aid)

    _bump_meta_updated(category)
    meta = _read_meta(category)

    return {
        "message": "Category file updated",
        "category": category,
        "filename": "meta.json",
        "content": {
            "category": meta.get("category", category),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
            "data": written,
        },
    }


def delete_category_record(category_id: str) -> dict:
    _require_category(category_id)

    members = storage.read_members(category_id)
    shutil.rmtree(storage.category_dir(category_id))

    for aid in members:
        cats = _asset_categories(aid)
        if not cats:
            path = storage.asset_path(aid)
            if path.exists():
                path.unlink()
            storage.remove_index_entry(aid)
        else:
            asset = _read_asset(aid)
            storage.update_index_entry(aid, asset, cats)

    return {"message": "Category and associated files deleted", "category_id": category_id}


def rename_category_record(old_category_id: str, new_name: str) -> dict:
    _require_category(old_category_id)
    if not new_name:
        raise HTTPException(status_code=400, detail="New name cannot be empty")

    new_category_id = storage.new_category_id(new_name)
    new_dir = storage.category_dir(new_category_id)
    if new_dir.exists():
        raise HTTPException(status_code=409, detail="Target category id already exists")

    storage.category_dir(old_category_id).rename(new_dir)

    meta = _read_meta(new_category_id)
    meta["category"] = new_name
    meta["category_id"] = new_category_id
    meta["updated_at"] = storage.now_iso()
    _write_meta(new_category_id, meta)

    members = storage.read_members(new_category_id)
    for aid in members:
        path = storage.asset_path(aid)
        if not path.exists():
            continue
        asset = storage.read_json(path)
        storage.update_index_entry(aid, asset, _asset_categories(aid))

    return {
        "message": "Category renamed",
        "old_id": old_category_id,
        "new_id": new_category_id,
    }


# --- Assets ---


def add_asset_to_category_record(category: str, asset_data: dict) -> dict:
    _require_category(category)

    asset_id = storage.new_asset_id()
    now = storage.now_iso()
    asset_data = {**asset_data, "id": asset_id, "created_at": now, "updated_at": now}
    _write_asset(asset_id, asset_data)
    _add_member(category, asset_id)
    _bump_meta_updated(category)
    storage.update_index_entry(asset_id, asset_data, _asset_categories(asset_id))

    return {
        "message": "Asset added successfully",
        "category": category,
        "asset_id": asset_id,
    }


def update_asset_in_record(category_id: str, asset_id: str, asset_data: dict) -> dict:
    _require_category(category_id)
    _require_asset(asset_id)
    if asset_id not in storage.read_members(category_id):
        raise HTTPException(status_code=404, detail="Asset not in this category")

    existing = _read_asset(asset_id)
    existing.update(asset_data)
    existing["updated_at"] = storage.now_iso()
    _write_asset(asset_id, existing)
    _bump_meta_updated(category_id)
    storage.update_index_entry(asset_id, existing, _asset_categories(asset_id))

    return {
        "message": "Asset updated successfully",
        "category_id": category_id,
        "asset_id": asset_id,
    }


def delete_asset_from_record(category_id: str, asset_id: str) -> dict:
    """Unlink from this category. If asset has no other categories, delete it."""
    _require_category(category_id)
    _require_asset(asset_id)
    if asset_id not in storage.read_members(category_id):
        raise HTTPException(status_code=404, detail="Asset not in this category")

    unlink_asset_from_category(category_id, asset_id)
    _bump_meta_updated(category_id)

    return {
        "message": "Asset deleted successfully",
        "category_id": category_id,
        "asset_id": asset_id,
    }


# --- Many-to-many ---


def link_asset_to_category(category_id: str, asset_id: str) -> dict:
    _require_category(category_id)
    _require_asset(asset_id)
    _add_member(category_id, asset_id)
    _bump_meta_updated(category_id)
    asset = _read_asset(asset_id)
    storage.update_index_entry(asset_id, asset, _asset_categories(asset_id))
    return {
        "message": "Asset linked to category",
        "category_id": category_id,
        "asset_id": asset_id,
        "categories": _asset_categories(asset_id),
    }


def unlink_asset_from_category(category_id: str, asset_id: str) -> dict:
    _require_category(category_id)
    _require_asset(asset_id)
    _remove_member(category_id, asset_id)

    cats = _asset_categories(asset_id)
    if not cats:
        path = storage.asset_path(asset_id)
        if path.exists():
            path.unlink()
        storage.remove_index_entry(asset_id)
    else:
        asset = _read_asset(asset_id)
        storage.update_index_entry(asset_id, asset, cats)

    return {
        "message": "Asset unlinked from category",
        "category_id": category_id,
        "asset_id": asset_id,
        "categories": cats,
        "deleted": not cats,
    }
