import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import jwt
import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.enums import UserRole


def _make_token(sub: str, expired: bool = False, **extra_claims) -> str:
    if expired:
        exp = datetime.now(timezone.utc) - timedelta(minutes=5)
    else:
        exp = datetime.now(timezone.utc) + timedelta(minutes=30)

    payload = {"sub": sub, "email": "test@example.com", "role": "user", "exp": exp}
    payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _make_credentials(token: str):
    return SimpleNamespace(credentials=token)


def _make_user(user_id: uuid.UUID):
    return SimpleNamespace(
        id=user_id,
        username="testuser",
        email="test@example.com",
        role=UserRole.USER,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.mark.asyncio
class TestGetCurrentUser:
    async def test_returns_user_for_valid_token(self):
        user_id = uuid.uuid4()
        token = _make_token(sub=str(user_id))
        credentials = _make_credentials(token)
        user = _make_user(user_id)

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: user

        result = await get_current_user(credentials=credentials, db=db)

        assert result.id == user_id
        assert result.username == "testuser"
        db.execute.assert_awaited_once()

    async def test_rejects_expired_token(self):
        token = _make_token(sub=str(uuid.uuid4()), expired=True)
        credentials = _make_credentials(token)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()
        db.execute.assert_not_awaited()

    async def test_rejects_invalid_token(self):
        credentials = _make_credentials("not-a-valid-jwt-token")
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db)

        assert exc_info.value.status_code == 401
        assert "Invalid token" in exc_info.value.detail
        db.execute.assert_not_awaited()

    async def test_rejects_token_with_wrong_secret(self):
        payload = {
            "sub": str(uuid.uuid4()),
            "email": "test@example.com",
            "role": "user",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        }
        token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")
        credentials = _make_credentials(token)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db)

        assert exc_info.value.status_code == 401
        db.execute.assert_not_awaited()

    async def test_rejects_token_without_sub_claim(self):
        exp = datetime.now(timezone.utc) + timedelta(minutes=30)
        payload = {"email": "test@example.com", "role": "user", "exp": exp}
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        credentials = _make_credentials(token)
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db)

        assert exc_info.value.status_code == 401
        assert "Invalid token payload" in exc_info.value.detail

    async def test_rejects_token_for_nonexistent_user(self):
        user_id = uuid.uuid4()
        token = _make_token(sub=str(user_id))
        credentials = _make_credentials(token)

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials=credentials, db=db)

        assert exc_info.value.status_code == 401
        assert "User not found" in exc_info.value.detail
