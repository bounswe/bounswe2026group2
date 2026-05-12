from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from starlette.responses import Response


@pytest.mark.asyncio
class TestHealthEndpoint:
    @patch("app.main.check_connection")
    @patch("app.main.engine")
    async def test_returns_ok_when_all_healthy(self, mock_engine, mock_check):
        from app.main import health

        response = Response()
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await health(response)

        assert result["status"] == "ok"
        assert result["db"] == "ok"
        assert result["storage"] == "ok"
        assert response.status_code == status.HTTP_200_OK

    @patch("app.main.check_connection")
    @patch("app.main.engine")
    async def test_returns_degraded_when_db_unreachable(self, mock_engine, mock_check):
        from app.main import health

        response = Response()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB connection refused"))
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await health(response)

        assert result["status"] == "degraded"
        assert "unreachable" in result["db"]
        assert result["storage"] == "ok"
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("app.main.check_connection", side_effect=Exception("Storage down"))
    @patch("app.main.engine")
    async def test_returns_degraded_when_storage_unreachable(self, mock_engine, mock_check):
        from app.main import health

        response = Response()
        mock_conn = AsyncMock()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await health(response)

        assert result["status"] == "degraded"
        assert result["db"] == "ok"
        assert "unreachable" in result["storage"]
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

    @patch("app.main.check_connection", side_effect=Exception("Storage down"))
    @patch("app.main.engine")
    async def test_returns_degraded_when_both_unreachable(self, mock_engine, mock_check):
        from app.main import health

        response = Response()
        mock_engine.connect.return_value.__aenter__ = AsyncMock(side_effect=Exception("DB down"))
        mock_engine.connect.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await health(response)

        assert result["status"] == "degraded"
        assert "unreachable" in result["db"]
        assert "unreachable" in result["storage"]
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
