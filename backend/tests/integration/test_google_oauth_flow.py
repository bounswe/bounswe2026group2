"""Integration tests for Google OAuth flow — mocks Google HTTP endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.db.user import User
from app.models.user import UserRegisterRequest
from app.services.auth_service import google_oauth_login, register_user

FAKE_TOKENS = {"access_token": "fake-access-token", "token_type": "Bearer"}
FAKE_USERINFO = {
    "id": "google-sub-123",
    "email": "oauth@example.com",
    "name": "OAuth User",
}


def _make_mock_response(json_data: dict, status_code: int = 200):
    mock = MagicMock()
    mock.status_code = status_code
    mock.json.return_value = json_data
    return mock


@pytest.mark.asyncio
class TestGoogleOAuthNewUser:
    """New Google user gets a JWT and a persisted account."""

    async def test_new_google_user_creates_account_and_returns_token(self, db_session):
        with (
            patch(
                "app.services.auth_service._exchange_code",
                new=AsyncMock(return_value=FAKE_TOKENS),
            ),
            patch(
                "app.services.auth_service._get_google_userinfo",
                new=AsyncMock(return_value=FAKE_USERINFO),
            ),
        ):
            token_resp = await google_oauth_login(db_session, "fake-code")

        assert token_resp.access_token
        assert token_resp.token_type == "bearer"

        result = await db_session.execute(select(User).where(User.email == "oauth@example.com"))
        user = result.scalar_one()
        assert user.google_sub == "google-sub-123"
        assert user.password_hash is None
        assert user.display_name == "OAuth User"

    async def test_username_derived_from_email(self, db_session):
        with (
            patch(
                "app.services.auth_service._exchange_code",
                new=AsyncMock(return_value=FAKE_TOKENS),
            ),
            patch(
                "app.services.auth_service._get_google_userinfo",
                new=AsyncMock(return_value=FAKE_USERINFO),
            ),
        ):
            await google_oauth_login(db_session, "fake-code")

        result = await db_session.execute(select(User).where(User.email == "oauth@example.com"))
        user = result.scalar_one()
        assert user.username == "oauth"


@pytest.mark.asyncio
class TestGoogleOAuthExistingUser:
    """Existing email/password account gets google_sub linked on first OAuth login."""

    async def test_links_google_sub_to_existing_email_account(self, db_session):
        await register_user(
            db_session,
            UserRegisterRequest(
                username="existinguser",
                email="oauth@example.com",
                password="Existing1!",
            ),
        )

        with (
            patch(
                "app.services.auth_service._exchange_code",
                new=AsyncMock(return_value=FAKE_TOKENS),
            ),
            patch(
                "app.services.auth_service._get_google_userinfo",
                new=AsyncMock(return_value=FAKE_USERINFO),
            ),
        ):
            token_resp = await google_oauth_login(db_session, "fake-code")

        assert token_resp.access_token

        result = await db_session.execute(select(User).where(User.email == "oauth@example.com"))
        user = result.scalar_one()
        assert user.google_sub == "google-sub-123"
        assert user.username == "existinguser"

    async def test_second_oauth_login_uses_google_sub_lookup(self, db_session):
        with (
            patch(
                "app.services.auth_service._exchange_code",
                new=AsyncMock(return_value=FAKE_TOKENS),
            ),
            patch(
                "app.services.auth_service._get_google_userinfo",
                new=AsyncMock(return_value=FAKE_USERINFO),
            ),
        ):
            await google_oauth_login(db_session, "fake-code")
            token_resp = await google_oauth_login(db_session, "fake-code-2")

        assert token_resp.access_token
        result = await db_session.execute(select(User).where(User.google_sub == "google-sub-123"))
        assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
class TestGoogleOAuthErrorHandling:
    """Bad Google responses are surfaced as 401."""

    async def test_token_exchange_failure_raises_401(self, db_session):
        with patch(
            "app.services.auth_service._exchange_code",
            new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Google token exchange failed")),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await google_oauth_login(db_session, "bad-code")
        assert exc_info.value.status_code == 401

    async def test_userinfo_failure_raises_401(self, db_session):
        with (
            patch(
                "app.services.auth_service._exchange_code",
                new=AsyncMock(return_value=FAKE_TOKENS),
            ),
            patch(
                "app.services.auth_service._get_google_userinfo",
                new=AsyncMock(side_effect=HTTPException(status_code=401, detail="Failed to fetch Google user info")),
            ),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await google_oauth_login(db_session, "fake-code")
        assert exc_info.value.status_code == 401


@pytest.mark.asyncio
class TestGoogleOAuthUsernameCollision:
    """Username derived from email is made unique when it collides."""

    async def test_username_gets_suffix_on_collision(self, db_session):
        await register_user(
            db_session,
            UserRegisterRequest(
                username="oauth",
                email="other@example.com",
                password="Other123!",
            ),
        )

        with (
            patch(
                "app.services.auth_service._exchange_code",
                new=AsyncMock(return_value=FAKE_TOKENS),
            ),
            patch(
                "app.services.auth_service._get_google_userinfo",
                new=AsyncMock(return_value=FAKE_USERINFO),
            ),
        ):
            await google_oauth_login(db_session, "fake-code")

        result = await db_session.execute(select(User).where(User.email == "oauth@example.com"))
        user = result.scalar_one()
        assert user.username == "oauth1"
