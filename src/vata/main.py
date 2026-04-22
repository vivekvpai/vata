import json
from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel, Field
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

# --- Import Services ---
from .services.category_service import (
    create_category_record,
    list_categories_record,
    get_category_record,
    update_category_record,
    delete_category_record,
    rename_category_record,
    add_asset_to_category_record,
    update_asset_in_record,
    delete_asset_from_record,
    ensure_data_dir,
)
from .services.ai_service import fetch_ai_suggestions
from .services.decision_service import evaluate_nodes_for_query

app = FastAPI(title="Vata API")

@app.on_event("startup")
async def startup_event():
    ensure_data_dir()

# --- API Router ---
api_router = APIRouter(prefix="/api")

# --- Request Schemas ---

class CategoryCreateRequest(BaseModel):
    category: str = Field(..., min_length=1)
    data: dict = Field(default_factory=dict)

class CategoryUpdateRequest(BaseModel):
    data: dict = Field(default_factory=dict)

class CategoryRenameRequest(BaseModel):
    new_name: str = Field(..., min_length=1)

class AssetCreateRequest(BaseModel):
    main_content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)

class SuggestionRequest(BaseModel):
    main_content: str
    summary: str | None = None
    tags: list[str] = Field(default_factory=list)

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1)

# --- Routes ---

@api_router.get("/hello")
async def hello():
    return {"message": "Hello from Vata backend!"}


@api_router.post("/categories")
async def create_category(request: CategoryCreateRequest):
    return create_category_record(request.category.strip(), request.data)

@api_router.post("/categories/{category}/assets")
async def add_asset(category: str, request: AssetCreateRequest):
    return add_asset_to_category_record(category, request.dict())

@api_router.put("/categories/{category}/assets/{asset_id}")
async def update_asset(category: str, asset_id: str, request: AssetCreateRequest):
    return update_asset_in_record(category, asset_id, request.dict())

@api_router.delete("/categories/{category}/assets/{asset_id}")
async def delete_asset(category: str, asset_id: str):
    return delete_asset_from_record(category, asset_id)

@api_router.get("/categories")
async def list_categories():
    return list_categories_record()


@api_router.get("/categories/{category}")
async def get_category(category: str):
    return get_category_record(category)


@api_router.put("/categories/{category}")
async def update_category(category: str, request: CategoryUpdateRequest):
    return update_category_record(category, request.data)


@api_router.delete("/categories/{category}")
async def delete_category(category: str):
    return delete_category_record(category)


@api_router.patch("/categories/{category}/rename")
async def rename_category(category: str, request: CategoryRenameRequest):
    return rename_category_record(category, request.new_name.strip())


@api_router.post("/suggestions")
async def get_suggestions(request: SuggestionRequest):
    return await fetch_ai_suggestions(request.main_content, request.summary, request.tags)

@api_router.post("/query")
async def process_query(request: QueryRequest):
    return evaluate_nodes_for_query(request.query)

app.include_router(api_router)

# --- Static Frontend Serving ---
FRONTEND_DIR = Path(__file__).parent / "frontend_dist"
INDEX_FILE = FRONTEND_DIR / "index.html"

if INDEX_FILE.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return FileResponse(str(INDEX_FILE))
else:
    @app.get("/")
    async def root():
        return {
            "status": "Frontend not found",
            "message": "Please build the frontend using 'npm run build' inside the frontend/ directory."
        }
