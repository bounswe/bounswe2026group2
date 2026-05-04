import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.db.enums import UserRole
from app.models.user import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import login_user, register_user


def _make_user_entity(**overrides):
    base = {
        "id": uuid.uuid4(),
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "display_name": None,
        "role": UserRole.USER,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
class TestRegisterUser:
    async def test_register_success(self):
        payload = UserRegisterRequest(
            username="newuser",
            email="new@example.com",
            password="StrongPass1!",
            display_name="New User",
        )

        db = AsyncMock()
        # First execute: email check returns None
        # Second execute: username check returns None
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: None),
            MagicMock(scalar_one_or_none=lambda: None),
        ]

        async def _refresh_side_effect(user_obj):
            user_obj.id = uuid.uuid4()
            user_obj.role = UserRole.USER
            user_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        result = await register_user(db, payload)

        assert result.username == "newuser"
        assert result.email == "new@example.com"
        assert result.display_name == "New User"
        assert result.role == UserRole.USER
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_register_normalizes_email_to_lowercase(self):
        payload = UserRegisterRequest(
            username="newuser",
            email="Test@Example.COM",
            password="StrongPass1!",
        )

        db = AsyncMock()
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: None),
            MagicMock(scalar_one_or_none=lambda: None),
        ]

        async def _refresh_side_effect(user_obj):
            user_obj.id = uuid.uuid4()
            user_obj.role = UserRole.USER
            user_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        result = await register_user(db, payload)

        assert result.email == "test@example.com"

    async def test_register_rejects_duplicate_email(self):
        payload = UserRegisterRequest(
            username="newuser",
            email="existing@example.com",
            password="StrongPass1!",
        )

        existing_user = _make_user_entity(email="existing@example.com")
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: existing_user

        with pytest.raises(HTTPException) as exc_info:
            await register_user(db, payload)

        assert exc_info.value.status_code == 409
        assert "Email already registered" in exc_info.value.detail
        db.add.assert_not_called()

    async def test_register_rejects_duplicate_username(self):
        payload = UserRegisterRequest(
            username="takenuser",
            email="new@example.com",
            password="StrongPass1!",
        )

        existing_user = _make_user_entity(username="takenuser")
        db = AsyncMock()
        # First execute: email check returns None
        # Second execute: username check returns existing user
        db.execute.side_effect = [
            MagicMock(scalar_one_or_none=lambda: None),
            MagicMock(scalar_one_or_none=lambda: existing_user),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await register_user(db, payload)

        assert exc_info.value.status_code == 409
        assert "Username already taken" in exc_info.value.detail
        db.add.assert_not_called()


@pytest.mark.asyncio
class TestLoginUser:
    @patch("app.services.auth_service.verify_password", return_value=True)
    @patch("app.services.auth_service.create_access_token", return_value="fake-jwt-token")
    async def test_login_success(self, mock_token, mock_verify):
        payload = UserLoginRequest(email="test@example.com", password="StrongPass1!")
        user = _make_user_entity()

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: user

        result = await login_user(db, payload)

        assert result.access_token == "fake-jwt-token"
        assert result.token_type == "bearer"
        mock_verify.assert_called_once_with("StrongPass1!", user.password_hash)
        mock_token.assert_called_once_with(user)

    async def test_login_rejects_nonexistent_email(self):
        payload = UserLoginRequest(email="nobody@example.com", password="StrongPass1!")

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await login_user(db, payload)

        assert exc_info.value.status_code == 401
        assert "Invalid email or password" in exc_info.value.detail

    @patch("app.services.auth_service.verify_password", return_value=False)
    async def test_login_rejects_wrong_password(self, mock_verify):
        payload = UserLoginRequest(email="test@example.com", password="WrongPass1!")
        user = _make_user_entity()

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: user

        with pytest.raises(HTTPException) as exc_info:
            await login_user(db, payload)

        assert exc_info.value.status_code == 401
        assert "Invalid email or password" in exc_info.value.detail

    @patch("app.services.auth_service.verify_password", return_value=True)
    @patch("app.services.auth_service.create_access_token", return_value="fake-jwt-token")
    async def test_login_normalizes_email_to_lowercase(self, mock_token, mock_verify):
        payload = UserLoginRequest(email="Test@Example.COM", password="StrongPass1!")
        user = _make_user_entity(email="test@example.com")

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: user

        result = await login_user(db, payload)

        assert result.access_token == "fake-jwt-token"
