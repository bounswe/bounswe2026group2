import os

# Set required env vars before any app imports
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
os.environ["STORAGE_ENDPOINT"] = "http://localhost:9000"
os.environ["STORAGE_ACCESS_KEY"] = "test"
os.environ["STORAGE_SECRET_KEY"] = "test"

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

# Mock boto3 before app imports so storage.py doesn't need a real connection
import boto3
_real_client = boto3.client


def _mock_boto3_client(*args, **kwargs):
    if args and args[0] == "s3":
        mock = MagicMock()
        mock.list_buckets.return_value = {"Buckets": []}
        return mock
    return _real_client(*args, **kwargs)


_patcher = patch.object(boto3, "client", side_effect=_mock_boto3_client)
_patcher.start()

from httpx import ASGITransport, AsyncClient
from app.main import app, engine
from app.services.storage import check_connection


@pytest.fixture()
def mock_engine():
    """Mock the SQLAlchemy async engine so tests don't need a real DB."""
    mock = MagicMock()
    conn = AsyncMock()
    conn.execute = AsyncMock()
    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=False)
    mock.connect.return_value = ctx
    mock.dispose = AsyncMock()
    return mock


@pytest.fixture()
def mock_storage():
    """Mock the storage check so tests don't need MinIO."""
    with patch("app.main.check_connection") as m:
        yield m


@pytest.fixture()
async def client(mock_engine, mock_storage):
    """Async test client with mocked DB and storage."""
    with patch("app.main.engine", mock_engine):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
