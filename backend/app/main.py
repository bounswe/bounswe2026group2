from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db.session import engine
from app.routers.auth import router as auth_router
from app.routers.story import router as story_router
from app.routers.users import router as users_router
from app.services.storage import check_connection


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify the DB connection is reachable
    async with engine.connect():
        pass
    # Startup: verify storage backend is reachable
    check_connection()
    yield
    # Shutdown: release connection pool
    await engine.dispose()


app = FastAPI(
    title="Local History Story Map API",
    description=(
        "API for creating, discovering, and exploring stories tied to geographic locations "
        "and historical dates. Supports authentication, story CRUD, geographic/date filtering, "
        "full-text search, and media uploads."
    ),
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(story_router)
app.include_router(users_router)


@app.get("/")
def root():
    return {"message": "Local History Story Map API"}


@app.get("/health")
async def health():
    # Check DB connectivity
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"unreachable: {e}"

    # Check storage connectivity
    try:
        check_connection()
        storage_status = "ok"
    except Exception as e:
        storage_status = f"unreachable: {e}"

    all_ok = db_status == "ok" and storage_status == "ok"
    return {
        "status": "ok" if all_ok else "degraded",
        "db": db_status,
        "storage": storage_status,
    }
