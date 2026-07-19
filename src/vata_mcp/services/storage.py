"""Mongo-backed storage layer.

Uses a real `pymongo.MongoClient` when `VATA_MONGODB_URI` is set, otherwise
falls back to an in-memory `mongomock` client so the whole stack runs with
zero external services during local development. Swapping to real MongoDB
Atlas later is just setting the env var — no code changes needed.

Each asset belongs to exactly one category (`category_id` on the asset
document) — no many-to-many join collection. Deleting a category always
deletes its assets too.
"""

import os
from datetime import datetime, timezone

from ulid import ULID

_MONGODB_URI = os.getenv("VATA_MONGODB_URI")
_DB_NAME = os.getenv("VATA_MONGODB_DB", "vata")

_USING_REAL_MONGODB = bool(_MONGODB_URI)

if _USING_REAL_MONGODB:
    from pymongo import MongoClient

    _client = MongoClient(_MONGODB_URI)
    print(f"[vata-mcp] storage: using real MongoDB at {_MONGODB_URI!r}")
else:
    import mongomock

    _client = mongomock.MongoClient()
    print("[vata-mcp] storage: no VATA_MONGODB_URI set — using in-memory mongomock (dummy DB, data does not persist across restarts)")


def backend_info() -> dict:
    return {
        "backend": "mongodb" if _USING_REAL_MONGODB else "mongomock (in-memory, non-persistent)",
        "database": _DB_NAME,
        "persistent": _USING_REAL_MONGODB,
    }


_db = _client[_DB_NAME]

assets_col = _db["assets"]
categories_col = _db["categories"]

assets_col.create_index("category_id")
assets_col.create_index("title")
categories_col.create_index("category")


# --- ID / time helpers ---


def new_asset_id() -> str:
    return str(ULID())


def new_category_id(name: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in name).strip("_") or "category"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{slug}_{timestamp}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Categories ---


def insert_category(category_id: str, name: str, description: str = "") -> dict:
    now = now_iso()
    doc = {
        "_id": category_id,
        "category": name,
        "description": description or "",
        "created_at": now,
        "updated_at": now,
    }
    categories_col.insert_one(doc)
    return doc


def get_category(category_id: str) -> dict | None:
    return categories_col.find_one({"_id": category_id})


def find_category_by_name(name: str) -> dict | None:
    return categories_col.find_one({"category": name})


def list_categories() -> list[dict]:
    return list(categories_col.find({}))


def touch_category(category_id: str) -> None:
    categories_col.update_one({"_id": category_id}, {"$set": {"updated_at": now_iso()}})


def update_category_fields(category_id: str, fields: dict) -> None:
    patch = {k: v for k, v in fields.items() if v is not None}
    if not patch:
        return
    patch["updated_at"] = now_iso()
    categories_col.update_one({"_id": category_id}, {"$set": patch})


def count_categories() -> int:
    return categories_col.count_documents({})


def count_assets() -> int:
    return assets_col.count_documents({})


def rename_category(category_id: str, new_id: str, new_name: str) -> None:
    doc = categories_col.find_one({"_id": category_id})
    if not doc:
        return
    doc["_id"] = new_id
    doc["category"] = new_name
    doc["updated_at"] = now_iso()
    categories_col.delete_one({"_id": category_id})
    categories_col.insert_one(doc)
    assets_col.update_many({"category_id": category_id}, {"$set": {"category_id": new_id}})


def delete_category(category_id: str) -> None:
    categories_col.delete_one({"_id": category_id})


# --- Assets ---


def insert_asset(
    asset_id: str,
    category_id: str,
    title: str,
    content: str,
    description: str,
    tags: list[str],
) -> dict:
    now = now_iso()
    doc = {
        "_id": asset_id,
        "category_id": category_id,
        "title": title or "",
        "content": content,
        "description": description or "",
        "tags": sorted({t.strip().lower() for t in (tags or []) if t.strip()}),
        "created_at": now,
        "updated_at": now,
    }
    assets_col.insert_one(doc)
    return doc


def get_asset(asset_id: str) -> dict | None:
    return assets_col.find_one({"_id": asset_id})


def find_asset_by_title(title: str) -> dict | None:
    return assets_col.find_one({"title": {"$regex": f"^{title}$", "$options": "i"}})


def update_asset(asset_id: str, fields: dict) -> dict | None:
    patch = {}
    if fields.get("title") is not None:
        patch["title"] = fields["title"]
    if fields.get("content") is not None:
        patch["content"] = fields["content"]
    if fields.get("description") is not None:
        patch["description"] = fields["description"]
    if fields.get("tags") is not None:
        patch["tags"] = sorted({t.strip().lower() for t in fields["tags"] if t.strip()})
    if not patch:
        return get_asset(asset_id)
    patch["updated_at"] = now_iso()
    assets_col.update_one({"_id": asset_id}, {"$set": patch})
    return get_asset(asset_id)


def move_asset_category(asset_id: str, new_category_id: str) -> None:
    assets_col.update_one({"_id": asset_id}, {"$set": {"category_id": new_category_id, "updated_at": now_iso()}})


def delete_asset(asset_id: str) -> None:
    assets_col.delete_one({"_id": asset_id})


def delete_assets_in_category(category_id: str) -> list[str]:
    ids = [a["_id"] for a in assets_col.find({"category_id": category_id}, {"_id": 1})]
    assets_col.delete_many({"category_id": category_id})
    return ids


def list_all_assets() -> list[dict]:
    return list(assets_col.find({}))


def list_assets_in_category(category_id: str) -> list[dict]:
    return list(assets_col.find({"category_id": category_id}))


def count_assets_in_category(category_id: str) -> int:
    return assets_col.count_documents({"category_id": category_id})


def wipe_all() -> dict:
    """Delete every category and asset. Does not attempt dropDatabase — some
    Mongo users (e.g. scoped Atlas roles) aren't granted that privilege, so
    this clears collection contents instead, which any read/write role can do."""
    deleted_assets = assets_col.delete_many({}).deleted_count
    deleted_categories = categories_col.delete_many({}).deleted_count
    return {"deleted_categories": deleted_categories, "deleted_assets": deleted_assets}
