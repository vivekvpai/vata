import json
from datetime import datetime, timezone
from pathlib import Path
from fastapi import HTTPException

DATA_DIR = Path.home() / ".vata" / "data"
CATEGORY_REGISTRY_FILE = DATA_DIR / "category.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_category_registry() -> dict[str, list[str]]:
    ensure_data_dir()
    if not CATEGORY_REGISTRY_FILE.exists():
        return {}
    with CATEGORY_REGISTRY_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_category_registry(registry: dict[str, list[str]]) -> None:
    ensure_data_dir()
    with CATEGORY_REGISTRY_FILE.open("w", encoding="utf-8") as file:
        json.dump(registry, file, indent=2)


def build_category_filename(category: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{category}_{timestamp}.json"


def resolve_category_file(category_id: str) -> Path:
    registry = load_category_registry()
    
    # Optional logic: If they pass the base name implicitly, let's strictly rely on the key if we can.
    # The frontend is going to pass whatever is the Key.
    if category_id not in registry:
        raise HTTPException(status_code=404, detail="Category not found")

    file_path = DATA_DIR / f"{category_id}.json"
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Category file not found")

    return file_path


def read_json_file(file_path: Path) -> dict:
    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


def write_json_file(file_path: Path, payload: dict) -> None:
    ensure_data_dir()
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2)


def add_asset_to_category_record(category: str, asset_data: dict) -> dict:
    file_path = resolve_category_file(category)
    payload = read_json_file(file_path)
    
    if "data" not in payload:
        payload["data"] = {}
        
    # Build an epoch timestamp string
    asset_id = str(int(datetime.now(timezone.utc).timestamp()))
    asset_data["created_at"] = datetime.now(timezone.utc).isoformat()
    asset_data["updated_at"] = asset_data["created_at"]
    asset_data["id"] = asset_id
    
    payload["data"][asset_id] = asset_data
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    write_json_file(file_path, payload)
    
    return {
        "message": "Asset added successfully",
        "category": category,
        "asset_id": asset_id
    }

def create_category_record(category: str, data: dict = None) -> dict:
    if not category:
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    category_id = f"{category}_{timestamp}"
    filename_on_disk = f"{category_id}.json"
    
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "category": category, # base name
        "created_at": now,
        "updated_at": now,
        "data": data or {},
    }

    write_json_file(DATA_DIR / filename_on_disk, payload)

    registry = load_category_registry()
    # K: ID (angular_1234), V: base_name.json (angular.json)
    registry[category_id] = f"{category}.json"
    save_category_registry(registry)

    return {
        "message": "Category file created",
        "category_id": category_id,
        "filename": filename_on_disk,
    }


def list_categories_record() -> dict:
    return load_category_registry()


def get_category_record(category: str) -> dict:
    file_path = resolve_category_file(category)
    return {
        "category": category,
        "filename": file_path.name,
        "content": read_json_file(file_path),
    }


    write_json_file(file_path, payload)
 
def update_category_record(category: str, data: dict) -> dict:
    file_path = resolve_category_file(category)
    payload = read_json_file(file_path)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["data"] = data
    
    write_json_file(file_path, payload)

    return {
        "message": "Category file updated",
        "category": category,
        "filename": file_path.name,
        "content": payload,
    }

def update_asset_in_record(category_id: str, asset_id: str, asset_data: dict) -> dict:
    file_path = resolve_category_file(category_id)
    payload = read_json_file(file_path)
    
    if "data" not in payload:
        payload["data"] = {}
        
    if asset_id not in payload["data"]:
        raise HTTPException(status_code=404, detail="Asset not found")

    # Update existing asset
    payload["data"][asset_id].update(asset_data)
    payload["data"][asset_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    write_json_file(file_path, payload)
    
    return {
        "message": "Asset updated successfully",
        "category_id": category_id,
        "asset_id": asset_id
    }

def delete_asset_from_record(category_id: str, asset_id: str) -> dict:
    file_path = resolve_category_file(category_id)
    payload = read_json_file(file_path)
    
    if "data" not in payload or asset_id not in payload["data"]:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    payload["data"].pop(asset_id)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    write_json_file(file_path, payload)
    
    return {
        "message": "Asset deleted successfully",
        "category_id": category_id,
        "asset_id": asset_id
    }


def delete_category_record(category_id: str) -> dict:
    registry = load_category_registry()
    
    if category_id not in registry:
        raise HTTPException(status_code=404, detail="Category not found")
        
    registry.pop(category_id)
    
    file_path = DATA_DIR / f"{category_id}.json"
    if file_path.exists():
        file_path.unlink()

    save_category_registry(registry)

    return {"message": "Category and associated files deleted", "category_id": category_id}


def rename_category_record(old_category_id: str, new_name: str) -> dict:
    registry = load_category_registry()
    if old_category_id not in registry:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if not new_name:
        raise HTTPException(status_code=400, detail="New name cannot be empty")
        
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    new_category_id = f"{new_name}_{timestamp}"

    # Remove the old key
    registry.pop(old_category_id)
    
    old_file_path = DATA_DIR / f"{old_category_id}.json"
    new_file_path = DATA_DIR / f"{new_category_id}.json"
    
    if old_file_path.exists():
        # Update the payload's internal "category" reference too
        payload = read_json_file(old_file_path)
        payload["category"] = new_name
        write_json_file(old_file_path, payload)
        
        # Rename physical file
        old_file_path.rename(new_file_path)
            
    # Add new key-value per user request
    registry[new_category_id] = f"{new_name}.json"
        
    save_category_registry(registry)

    return {
        "message": "Category renamed",
        "old_id": old_category_id,
        "new_id": new_category_id
    }
