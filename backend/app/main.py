from contextlib import asynccontextmanager

from fastapi import FastAPI

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
def health():
    return {"status": "ok"}
