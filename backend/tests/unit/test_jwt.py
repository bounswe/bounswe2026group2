import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import jwt
import pytest

from app.core.config import settings
from app.services.auth_service import create_access_token, hash_password, verify_password


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "TestPass1!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("TestPass1!")
        assert verify_password("WrongPass1!", hashed) is False

    def test_hash_is_not_deterministic(self):
        h1 = hash_password("TestPass1!")
        h2 = hash_password("TestPass1!")
        assert h1 != h2  # bcrypt uses random salt


class TestJWTTokenCreation:
    def _make_mock_user(self):
        user = MagicMock()
        user.id = uuid.uuid4()
        user.email = "test@example.com"
        user.role.value = "user"
        return user

    def test_token_contains_correct_claims(self):
        user = self._make_mock_user()
        token = create_access_token(user)
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert payload["sub"] == str(user.id)
        assert payload["email"] == "test@example.com"
        assert payload["role"] == "user"
        assert "exp" in payload

    def test_token_has_expiration(self):
        user = self._make_mock_user()
        token = create_access_token(user)
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        now = datetime.now(timezone.utc)
        assert exp > now
        assert exp <= now + timedelta(minutes=settings.JWT_EXPIRE_MINUTES + 1)

    def test_token_is_verifiable(self):
        user = self._make_mock_user()
        token = create_access_token(user)
        # Should not raise
        jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )

    def test_token_fails_with_wrong_secret(self):
        user = self._make_mock_user()
        token = create_access_token(user)
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=[settings.JWT_ALGORITHM])

    def test_token_does_not_contain_password(self):
        user = self._make_mock_user()
        token = create_access_token(user)
        payload = jwt.decode(
            token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM]
        )
        assert "password" not in payload
        assert "password_hash" not in payload
