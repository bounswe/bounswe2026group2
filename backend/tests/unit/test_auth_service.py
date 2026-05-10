import io
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.db.enums import UserRole
from app.models.user import UserLoginRequest, UserPasswordChangeRequest, UserProfileUpdateRequest, UserRegisterRequest
from app.services.auth_service import (
    change_user_password,
    get_user_profile,
    login_user,
    register_user,
    update_user_profile,
    upload_user_avatar,
)


def _make_user_entity(**overrides):
    base = {
        "id": uuid.uuid4(),
        "username": "testuser",
        "email": "test@example.com",
        "password_hash": "hashed_password",
        "display_name": None,
        "bio": None,
        "location": None,
        "avatar_bucket_name": None,
        "avatar_storage_key": None,
        "role": UserRole.USER,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        filename=filename,
        file=io.BytesIO(content),
        headers=Headers({"content-type": content_type}),
    )


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
        mock_verify.assert_called_once_with("StrongPass1!", user.password_hash)
        mock_token.assert_called_once_with(user)


class TestGetUserProfile:
    def test_maps_extended_profile_fields(self):
        user = _make_user_entity(
            display_name="Test User",
            bio="Archivist",
            location="Istanbul, Turkey",
            avatar_bucket_name="images",
            avatar_storage_key="users/abc/avatar/photo.png",
        )

        result = get_user_profile(user)

        assert result.display_name == "Test User"
        assert result.bio == "Archivist"
        assert result.location == "Istanbul, Turkey"
        assert result.avatar_url.endswith("/images/users/abc/avatar/photo.png")


@pytest.mark.asyncio
class TestUpdateUserProfile:
    async def test_updates_only_provided_fields(self):
        user = _make_user_entity(display_name="Old Name", bio="Old bio", location="Old place")
        payload = UserProfileUpdateRequest(display_name="New Name")
        db = AsyncMock()

        result = await update_user_profile(db, user, payload)

        assert result.display_name == "New Name"
        assert result.bio == "Old bio"
        assert result.location == "Old place"
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(user)

    async def test_allows_clearing_profile_fields_with_blank_strings(self):
        user = _make_user_entity(display_name="Name", bio="Bio", location="Place")
        payload = UserProfileUpdateRequest(display_name="   ", bio="", location=" ")
        db = AsyncMock()

        result = await update_user_profile(db, user, payload)

        assert result.display_name is None
        assert result.bio is None
        assert result.location is None


@pytest.mark.asyncio
class TestUploadUserAvatar:
    async def test_uploads_avatar_and_returns_profile_url(self):
        user = _make_user_entity(
            avatar_bucket_name="images",
            avatar_storage_key="users/old/avatar/old.png",
        )
        file = _make_upload_file("avatar.png", b"avatar-bytes", "image/png")
        db = AsyncMock()

        with (
            patch("app.services.auth_service.upload_bytes") as mock_upload,
            patch("app.services.auth_service.delete_object") as mock_delete,
        ):
            result = await upload_user_avatar(db, user, file)

        assert result.avatar_url is not None
        assert "/images/users/" in result.avatar_url
        mock_upload.assert_called_once()
        mock_delete.assert_called_once_with(
            bucket_name="images",
            storage_key="users/old/avatar/old.png",
        )
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(user)

    async def test_rejects_unsupported_avatar_type(self):
        user = _make_user_entity()
        file = _make_upload_file("avatar.txt", b"not-an-image", "text/plain")
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await upload_user_avatar(db, user, file)

        assert exc_info.value.status_code == 422
        db.commit.assert_not_awaited()

    async def test_rejects_empty_avatar(self):
        user = _make_user_entity()
        file = _make_upload_file("avatar.png", b"", "image/png")
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await upload_user_avatar(db, user, file)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Uploaded file is empty"


@pytest.mark.asyncio
class TestChangeUserPassword:
    @patch("app.services.auth_service.hash_password", return_value="new-hash")
    @patch("app.services.auth_service.verify_password", return_value=True)
    async def test_changes_password_when_current_password_matches(self, mock_verify, mock_hash):
        user = _make_user_entity(password_hash="old-hash")
        payload = UserPasswordChangeRequest(
            current_password="OldPass1!",
            new_password="NewPass1!",
        )
        db = AsyncMock()

        await change_user_password(db, user, payload)

        assert user.password_hash == "new-hash"
        mock_verify.assert_called_once_with("OldPass1!", "old-hash")
        mock_hash.assert_called_once_with("NewPass1!")
        db.commit.assert_awaited_once()

    @patch("app.services.auth_service.verify_password", return_value=False)
    async def test_rejects_wrong_current_password(self, mock_verify):
        user = _make_user_entity(password_hash="old-hash")
        payload = UserPasswordChangeRequest(
            current_password="WrongPass1!",
            new_password="NewPass1!",
        )
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await change_user_password(db, user, payload)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Current password is incorrect"
        mock_verify.assert_called_once_with("WrongPass1!", "old-hash")
        db.commit.assert_not_awaited()
