import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.mark.anyio
async def test_health_all_ok(client):
    """When both DB and storage are reachable, status is ok."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db"] == "ok"
    assert data["storage"] == "ok"


@pytest.mark.anyio
async def test_health_db_down(client, mock_engine):
    """When DB is unreachable, status is degraded."""
    conn_ctx = AsyncMock()
    conn_ctx.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("connection refused"))
    conn_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_engine.connect.return_value = conn_ctx

    resp = await client.get("/health")
    data = resp.json()
    assert data["status"] == "degraded"
    assert "unreachable" in data["db"]
    assert data["storage"] == "ok"


@pytest.mark.anyio
async def test_health_storage_down(client, mock_storage):
    """When storage is unreachable, status is degraded."""
    mock_storage.side_effect = ConnectionError("storage down")

    resp = await client.get("/health")
    data = resp.json()
    assert data["status"] == "degraded"
    assert data["db"] == "ok"
    assert "unreachable" in data["storage"]


@pytest.mark.anyio
async def test_health_both_down(client, mock_engine, mock_storage):
    """When both services are down, status is degraded."""
    conn_ctx = AsyncMock()
    conn_ctx.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("db down"))
    conn_ctx.__aexit__ = AsyncMock(return_value=False)
    mock_engine.connect.return_value = conn_ctx
    mock_storage.side_effect = ConnectionError("storage down")

    resp = await client.get("/health")
    data = resp.json()
    assert data["status"] == "degraded"
    assert "unreachable" in data["db"]
    assert "unreachable" in data["storage"]
