from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os
from sqlalchemy import select
from app.core.database import init_db, async_session
from app.core.config import settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.system_settings import SystemSettings
from app.services.vector_store.factory import set_vector_store_type
from app.api import auth, workspaces, chats, documents, admin, notes, v1


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    os.makedirs(settings.DOCUMENTS_DIR, exist_ok=True)
    os.makedirs(settings.ORIGINALS_DIR, exist_ok=True)
    os.makedirs(settings.MARKDOWN_DIR, exist_ok=True)
    
    await init_db()
    
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        admin_user = result.scalar_one_or_none()
        
        if not admin_user:
            admin_user = User(
                email=settings.ADMIN_EMAIL,
                password_hash=get_password_hash(settings.ADMIN_PASSWORD),
                name="Admin",
                role="admin"
            )
            db.add(admin_user)
            await db.commit()
            print(f"Created admin user: {settings.ADMIN_EMAIL}")
        
        # Load vector_store setting from DB (if set by admin)
        vs_result = await db.execute(
            select(SystemSettings).where(SystemSettings.key == "vector_store")
        )
        vs_setting = vs_result.scalar_one_or_none()
        if vs_setting and vs_setting.value in ("qdrant", "lancedb"):
            set_vector_store_type(vs_setting.value)
            print(f"Vector store from DB setting: {vs_setting.value}")
    
    yield


app = FastAPI(
    title=settings.APP_NAME,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(workspaces.router)
app.include_router(chats.router)
app.include_router(documents.router)
app.include_router(admin.router)
app.include_router(notes.router)
app.include_router(v1.router)  # Simple API for integrations


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}


@app.get("/api/health/qdrant")
async def qdrant_health_check():
    from app.services.rag_service import rag_service
    try:
        collections = rag_service.client.get_collections()
        return {"status": "ok", "collections": len(collections.collections)}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


# Static directory paths to check
STATIC_PATHS = [
    "/app/static",  # Docker container
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "static")),  # Local dev
]

def get_static_dir():
    """Find the static directory"""
    for path in STATIC_PATHS:
        if os.path.exists(path) and os.path.isdir(path):
            return path
    return None

# Mount static files for assets if directory exists
static_dir = get_static_dir()
if static_dir:
    assets_dir = os.path.join(static_dir, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

# SPA fallback - serve index.html for all non-API routes
@app.get("/{full_path:path}")
async def serve_spa(request: Request, full_path: str):
    # Don't serve index.html for API routes
    if full_path.startswith("api/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Not Found")
    
    static_dir = get_static_dir()
    if not static_dir:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Static files not found")
    
    index_path = os.path.join(static_dir, "index.html")
    
    # Try to serve static file first
    file_path = os.path.join(static_dir, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    
    # Fallback to index.html for SPA routing
    if os.path.exists(index_path):
        return FileResponse(index_path)
    
    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail="index.html not found")
