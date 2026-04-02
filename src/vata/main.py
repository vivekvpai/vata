import os
from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

app = FastAPI(title="Vata API")

# --- API Router ---
api_router = APIRouter(prefix="/api")

@api_router.get("/hello")
async def hello():
    return {"message": "Hello from Vata backend!"}

app.include_router(api_router)

# --- Static Frontend Serving ---
# Locate the frontend_dist directory relative to this file
FRONTEND_DIR = Path(__file__).parent / "frontend_dist"

# Check if the frontend has been built yet
if FRONTEND_DIR.exists() and any(FRONTEND_DIR.iterdir()):
    # Mount the built frontend files
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

    # Fallback to index.html for Single Page Application (SPA) routing
    @app.exception_handler(404)
    async def not_found_handler(request, exc):
        return FileResponse(FRONTEND_DIR / "index.html")
else:
    # Error message when frontend is not built
    @app.get("/")
    async def root():
        return {
            "status": "Frontend not found",
            "message": "Please build the frontend using 'npm run build' inside the frontend/ directory."
        }
