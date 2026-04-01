import pytest


@pytest.mark.anyio
async def test_root_returns_api_message(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "Local History Story Map API"}
