"""GroupOps Intelligence Hub - FastAPI entry point."""

import logging
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from server.routes import api
from server.db import reset_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("GroupOps Intelligence Hub starting up")
    yield
    logger.info("GroupOps Intelligence Hub shutting down")
    reset_connection()


app = FastAPI(
    title="GroupOps Intelligence Hub",
    description="Unified operational intelligence for energy & utilities operations teams",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount API routes
app.include_router(api)

# Serve React frontend
frontend_dist = Path(__file__).parent / "frontend" / "dist"

if frontend_dist.exists():
    # Serve static assets (JS, CSS, images)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Serve other static files (favicon, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        fav = frontend_dist / "favicon.ico"
        if fav.exists():
            return FileResponse(str(fav))
        return FileResponse(str(frontend_dist / "index.html"))

    # SPA fallback - serve index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't serve SPA for API routes
        if full_path.startswith("api/"):
            return {"error": "Not found"}, 404
        # Check if it's a static file
        file_path = frontend_dist / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(frontend_dist / "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "app": "GroupOps Intelligence Hub",
            "status": "Backend running. Frontend not built yet.",
            "endpoints": [
                "/api/health-summary",
                "/api/active-alarms",
                "/api/maintenance-queue",
                "/api/fault-wo-gap",
                "/api/chat",
            ],
        }


if __name__ == "__main__":
    import uvicorn
    import os

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
