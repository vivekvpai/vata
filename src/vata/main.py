import json
from datetime import datetime, timezone
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Vata API")

# --- API Router ---
api_router = APIRouter(prefix="/api")

DATA_DIR = Path(__file__).parent / "data"
CATEGORY_REGISTRY_FILE = DATA_DIR / "category.json"


class CategoryCreateRequest(BaseModel):
    category: str = Field(..., min_length=1)
    data: dict = Field(default_factory=dict)


class CategoryUpdateRequest(BaseModel):
    data: dict = Field(default_factory=dict)


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


def resolve_category_file(category: str) -> Path:
    registry = load_category_registry()
    filenames = registry.get(category)
    if not filenames:
        raise HTTPException(status_code=404, detail="Category not found")

    file_path = DATA_DIR / filenames[-1]
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

@api_router.get("/hello")
async def hello():
    return {"message": "Hello from Vata backend!"}


@api_router.post("/categories")
async def create_category(request: CategoryCreateRequest):
    category = request.category.strip()
    if not category:
        raise HTTPException(status_code=400, detail="Category cannot be empty")

    filename = build_category_filename(category)
    payload = {
        "category": category,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "data": request.data,
    }

    write_json_file(DATA_DIR / filename, payload)

    registry = load_category_registry()
    registry.setdefault(category, []).append(filename)
    save_category_registry(registry)

    return {
        "message": "Category file created",
        "category": category,
        "filename": filename,
    }


@api_router.get("/categories")
async def list_categories():
    return load_category_registry()


@api_router.get("/categories/{category}")
async def get_category(category: str):
    registry = load_category_registry()
    filenames = registry.get(category)
    if not filenames:
        raise HTTPException(status_code=404, detail="Category not found")

    file_path = resolve_category_file(category)
    return {
        "category": category,
        "filename": file_path.name,
        "files": filenames,
        "content": read_json_file(file_path),
    }


@api_router.put("/categories/{category}")
async def update_category(category: str, request: CategoryUpdateRequest):
    file_path = resolve_category_file(category)
    payload = read_json_file(file_path)
    payload["updated_at"] = datetime.now(timezone.utc).isoformat()
    payload["data"] = request.data
    write_json_file(file_path, payload)

    return {
        "message": "Category file updated",
        "category": category,
        "filename": file_path.name,
        "content": payload,
    }


@api_router.delete("/categories/{category}")
async def delete_category(category: str):
    registry = load_category_registry()
    filenames = registry.get(category)
    if not filenames:
        raise HTTPException(status_code=404, detail="Category not found")

    for filename in filenames:
        file_path = DATA_DIR / filename
        if file_path.exists():
            file_path.unlink()

    registry.pop(category, None)
    save_category_registry(registry)

    return {"message": "Category deleted", "category": category}

app.include_router(api_router)

# --- Static Frontend Serving ---
# Locate the frontend_dist directory relative to this file
FRONTEND_DIR = Path(__file__).parent / "frontend_dist"

# Check if the frontend has been built (requires index.html)
INDEX_FILE = FRONTEND_DIR / "index.html"

if INDEX_FILE.exists():
    # Mount the built frontend files
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

    # Fallback to index.html for Single Page Application (SPA) routing
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return FileResponse(str(INDEX_FILE))
else:
    # Error message when frontend is not built
    @app.get("/")
    async def root():
        return {
            "status": "Frontend not found",
            "message": "Please build the frontend using 'npm run build' inside the frontend/ directory."
        }
