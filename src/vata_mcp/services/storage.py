"""Mongo-backed storage layer.

Uses a real `pymongo.MongoClient` when `VATA_MONGODB_URI` is set, otherwise
falls back to an in-memory `mongomock` client so the whole stack runs with
zero external services during local development. Swapping to real MongoDB
Atlas later is just setting the env var — no code changes needed.
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
members_col = _db["category_members"]

members_col.create_index([("category_id", 1), ("asset_id", 1)], unique=True)
members_col.create_index("asset_id")
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


def update_category_description(category_id: str, description: str) -> None:
    categories_col.update_one(
        {"_id": category_id},
        {"$set": {"description": description, "updated_at": now_iso()}},
    )


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
    members_col.update_many({"category_id": category_id}, {"$set": {"category_id": new_id}})


def delete_category(category_id: str) -> None:
    categories_col.delete_one({"_id": category_id})


# --- Assets ---


def insert_asset(asset_id: str, main_content: str, summary: str, tags: list[str]) -> dict:
    now = now_iso()
    doc = {
        "_id": asset_id,
        "main_content": main_content,
        "summary": summary or "",
        "tags": sorted({t.strip().lower() for t in (tags or []) if t.strip()}),
        "created_at": now,
        "updated_at": now,
    }
    assets_col.insert_one(doc)
    return doc


def get_asset(asset_id: str) -> dict | None:
    return assets_col.find_one({"_id": asset_id})


def update_asset(asset_id: str, fields: dict) -> dict | None:
    patch = {}
    if "main_content" in fields and fields["main_content"] is not None:
        patch["main_content"] = fields["main_content"]
    if "summary" in fields and fields["summary"] is not None:
        patch["summary"] = fields["summary"]
    if "tags" in fields and fields["tags"] is not None:
        patch["tags"] = sorted({t.strip().lower() for t in fields["tags"] if t.strip()})
    if not patch:
        return get_asset(asset_id)
    patch["updated_at"] = now_iso()
    assets_col.update_one({"_id": asset_id}, {"$set": patch})
    return get_asset(asset_id)


def delete_asset(asset_id: str) -> None:
    assets_col.delete_one({"_id": asset_id})


def list_all_assets() -> list[dict]:
    return list(assets_col.find({}))


# --- Membership (many-to-many) ---


def add_member(category_id: str, asset_id: str) -> None:
    members_col.update_one(
        {"category_id": category_id, "asset_id": asset_id},
        {"$setOnInsert": {"category_id": category_id, "asset_id": asset_id}},
        upsert=True,
    )


def remove_member(category_id: str, asset_id: str) -> None:
    members_col.delete_one({"category_id": category_id, "asset_id": asset_id})


def categories_for_asset(asset_id: str) -> list[str]:
    return [m["category_id"] for m in members_col.find({"asset_id": asset_id})]


def members_of_category(category_id: str) -> list[str]:
    return [m["asset_id"] for m in members_col.find({"category_id": category_id})]


def remove_all_members_of_category(category_id: str) -> list[str]:
    asset_ids = members_of_category(category_id)
    members_col.delete_many({"category_id": category_id})
    return asset_ids


def remove_all_members_of_asset(asset_id: str) -> None:
    members_col.delete_many({"asset_id": asset_id})
