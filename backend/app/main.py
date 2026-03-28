from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from app.db.session import engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: verify the DB connection is reachable
    async with engine.connect():
        pass
    yield
    # Shutdown: release connection pool
    await engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.get("/")
def root():
    return {"message": "Local History Story Map API"}


@app.get("/health")
async def health():
    # Check DB connectivity — returns degraded status instead of crashing
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"unreachable: {e}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "db": db_status,
    }
