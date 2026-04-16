from unittest.mock import MagicMock

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.base import Base
from app.db.media_file import MediaFile  # noqa: F401
from app.db.session import get_db
from app.db.story import Story  # noqa: F401

# Import all models so Base.metadata knows about them
from app.db.user import User  # noqa: F401

# Build the async DB URL
_url = settings.DATABASE_URL
if _url.startswith("postgresql://"):
    _url = _url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _url.startswith("postgres://"):
    _url = _url.replace("postgres://", "postgresql+asyncpg://", 1)


@pytest_asyncio.fixture
async def db_session():
    """Provide a per-test engine + session so everything shares one event loop."""
    engine = create_async_engine(_url, echo=False)

    # Reset the schema first so stale tables from earlier runs don't survive
    # and silently bypass new columns added to the ORM models.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    session = session_factory()

    yield session

    # Teardown: close session, drop tables, dispose engine
    await session.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    """Async HTTP client wired to the FastAPI app with test DB session."""
    from app.main import app

    # Override storage check so tests don't need MinIO
    from app.services import storage

    original_check = storage.check_connection
    storage.check_connection = MagicMock()

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
    storage.check_connection = original_check
