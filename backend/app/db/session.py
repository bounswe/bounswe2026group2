import logging
import logging.handlers
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# Supabase (and most managed Postgres) give you a postgresql:// URL.
# SQLAlchemy async needs postgresql+asyncpg://, so we swap the scheme here.
# We only replace if the URL doesn't already have the correct scheme.
_raw_url = settings.DATABASE_URL
if _raw_url.startswith("postgresql+asyncpg://"):
    _url = _raw_url
elif _raw_url.startswith("postgresql://"):
    _url = _raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)
elif _raw_url.startswith("postgres://"):
    _url = _raw_url.replace("postgres://", "postgresql+asyncpg://", 1)
else:
    raise ValueError(
        f"DATABASE_URL has an unexpected scheme. Expected postgresql:// or postgres://, got: {_raw_url[:30]!r}"
    )

# SQL query logging
# ─────────────────
# When LOG_SQL=true in .env, every SQL statement is appended to logs/sql.log.
# The file rotates at 5 MB and keeps the last 3 rotated files so it never
# grows unbounded.
# To read live: tail -f backend/logs/sql.log
if settings.LOG_SQL:
    _log_path = Path(__file__).resolve().parents[3] / "logs" / "sql.log"
    _log_path.parent.mkdir(exist_ok=True)

    _handler = logging.handlers.RotatingFileHandler(_log_path, maxBytes=5 * 1024 * 1024, backupCount=3)
    _handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))

    _sql_logger = logging.getLogger("sqlalchemy.engine")
    _sql_logger.setLevel(logging.INFO)
    _sql_logger.addHandler(_handler)
    _sql_logger.propagate = False  # don't also print to terminal

engine = create_async_engine(_url, echo=settings.LOG_SQL)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
