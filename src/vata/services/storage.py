import json
import os
from datetime import datetime, timezone
from pathlib import Path

from ulid import ULID

DATA_DIR = Path.home() / ".vata" / "data"
ASSETS_DIR = DATA_DIR / "assets"
CATEGORIES_DIR = DATA_DIR / "categories"
INDEX_FILE = DATA_DIR / "index.json"


# --- Setup ---


def ensure_data_dir() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    CATEGORIES_DIR.mkdir(parents=True, exist_ok=True)


def ensure_category_dir(category_id: str) -> None:
    category_dir(category_id).mkdir(parents=True, exist_ok=True)


# --- Path helpers ---


def asset_path(asset_id: str) -> Path:
    return ASSETS_DIR / f"{asset_id}.json"


def category_dir(category_id: str) -> Path:
    return CATEGORIES_DIR / category_id


def meta_path(category_id: str) -> Path:
    return category_dir(category_id) / "meta.json"


def members_path(category_id: str) -> Path:
    return category_dir(category_id) / "members.json"


# --- Atomic JSON IO ---


def read_json(path: Path) -> dict | list:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    os.replace(tmp, path)


# --- Listings ---


def list_category_ids() -> list[str]:
    if not CATEGORIES_DIR.exists():
        return []
    return sorted(p.name for p in CATEGORIES_DIR.iterdir() if p.is_dir())


def list_asset_ids() -> list[str]:
    if not ASSETS_DIR.exists():
        return []
    return sorted(p.stem for p in ASSETS_DIR.iterdir() if p.is_file() and p.suffix == ".json")


def read_members(category_id: str) -> list[str]:
    p = members_path(category_id)
    if not p.exists():
        return []
    data = read_json(p)
    return data if isinstance(data, list) else []


def write_members(category_id: str, members: list[str]) -> None:
    write_json_atomic(members_path(category_id), members)


# --- ID generation ---


def new_asset_id() -> str:
    return str(ULID())


def new_category_id(name: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{name}_{timestamp}"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# --- Index (rebuildable cache) ---


def _index_entry(asset: dict, categories: list[str]) -> dict:
    content = asset.get("main_content", "") or ""
    return {
        "summary": asset.get("summary", "") or "",
        "tags": list(asset.get("tags", []) or []),
        "content_snippet": content[:200],
        "categories": list(categories),
        "updated_at": asset.get("updated_at", ""),
    }


def load_index() -> dict[str, dict]:
    if not INDEX_FILE.exists():
        return {}
    data = read_json(INDEX_FILE)
    return data if isinstance(data, dict) else {}


def save_index(index: dict[str, dict]) -> None:
    write_json_atomic(INDEX_FILE, index)


def update_index_entry(asset_id: str, asset: dict, categories: list[str]) -> None:
    index = load_index()
    index[asset_id] = _index_entry(asset, categories)
    save_index(index)


def remove_index_entry(asset_id: str) -> None:
    index = load_index()
    if asset_id in index:
        index.pop(asset_id)
        save_index(index)


def rebuild_index() -> dict[str, dict]:
    """Rebuild index.json from filesystem. Source of truth = files."""
    membership: dict[str, list[str]] = {}
    for cid in list_category_ids():
        for aid in read_members(cid):
            membership.setdefault(aid, []).append(cid)

    index: dict[str, dict] = {}
    for aid in list_asset_ids():
        try:
            asset = read_json(asset_path(aid))
        except Exception:
            continue
        if not isinstance(asset, dict):
            continue
        index[aid] = _index_entry(asset, membership.get(aid, []))

    save_index(index)
    return index
