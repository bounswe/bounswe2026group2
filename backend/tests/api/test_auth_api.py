import pytest

from tests.factories.user_factory import make_login_payload, make_user_payload


@pytest.mark.asyncio
class TestRegistrationAPI:
    """API test for registration endpoint. Covers #130."""

    async def test_register_success(self, client):
        payload = make_user_payload(
            username="apiuser",
            email="api@example.com",
            password="ApiPass1!",
            display_name="API User",
        )
        resp = await client.post("/auth/register", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["username"] == "apiuser"
        assert data["email"] == "api@example.com"
        assert data["display_name"] == "API User"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data
        assert "password" not in data
        assert "password_hash" not in data

    async def test_register_duplicate_email(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="first",
                email="same@example.com",
                password="ApiPass1!",
                display_name=None,
            ),
        )
        resp = await client.post(
            "/auth/register",
            json=make_user_payload(
                username="second",
                email="same@example.com",
                password="ApiPass1!",
                display_name=None,
            ),
        )
        assert resp.status_code == 409

    async def test_register_weak_password(self, client):
        resp = await client.post(
            "/auth/register",
            json=make_user_payload(
                username="weakuser",
                email="weak@example.com",
                password="nodigits",
                display_name=None,
            ),
        )
        assert resp.status_code == 422

    async def test_register_invalid_email(self, client):
        resp = await client.post(
            "/auth/register",
            json=make_user_payload(
                username="bademail",
                email="not-valid",
                password="ApiPass1!",
                display_name=None,
            ),
        )
        assert resp.status_code == 422

    async def test_register_missing_fields(self, client):
        # Missing username
        resp = await client.post(
            "/auth/register",
            json={
                "email": "missing@example.com",
                "password": "ApiPass1!",
            },
        )
        assert resp.status_code == 422

        # Missing email
        resp = await client.post(
            "/auth/register",
            json={
                "username": "missingmail",
                "password": "ApiPass1!",
            },
        )
        assert resp.status_code == 422

        # Missing password
        resp = await client.post(
            "/auth/register",
            json={
                "username": "misspwd",
                "email": "misspwd@example.com",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestLoginAPI:
    """API test for login endpoint. Covers #131."""

    async def test_login_success(self, client):
        # Register first
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="loginuser",
                email="login@example.com",
                password="LoginPass1!",
                display_name=None,
            ),
        )
        resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="login@example.com", password="LoginPass1!"),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="wrongpw",
                email="wrongpw@example.com",
                password="CorrectPass1!",
                display_name=None,
            ),
        )
        resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="wrongpw@example.com", password="WrongPass1!"),
        )
        assert resp.status_code == 401

    async def test_login_nonexistent_email(self, client):
        resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="ghost@example.com", password="AnyPass1!"),
        )
        assert resp.status_code == 401

    async def test_login_missing_fields(self, client):
        # Missing email
        resp = await client.post(
            "/auth/login",
            json={
                "password": "AnyPass1!",
            },
        )
        assert resp.status_code == 422

        # Missing password
        resp = await client.post(
            "/auth/login",
            json={
                "email": "some@example.com",
            },
        )
        assert resp.status_code == 422


@pytest.mark.asyncio
class TestTokenVerificationAPI:
    """API test for token verification middleware. Covers #132."""

    async def test_me_with_valid_token(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="meuser",
                email="me@example.com",
                password="MePass1!",
                display_name=None,
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="me@example.com", password="MePass1!"),
        )
        token = login_resp.json()["access_token"]

        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "meuser"
        assert data["email"] == "me@example.com"
        assert data["bio"] is None
        assert data["location"] is None
        assert data["avatar_url"] is None

    async def test_me_without_token(self, client):
        resp = await client.get("/auth/me")
        assert resp.status_code == 401 or resp.status_code == 403

    async def test_me_with_invalid_token(self, client):
        resp = await client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert resp.status_code == 401

    async def test_me_with_expired_token(self, client):
        from datetime import datetime, timedelta, timezone

        import jwt

        from app.core.config import settings

        expired_payload = {
            "sub": "00000000-0000-0000-0000-000000000000",
            "email": "expired@example.com",
            "role": "user",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(expired_payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        resp = await client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert resp.status_code == 401


@pytest.mark.asyncio
<<<<<<< HEAD
class TestProfileUpdateAPI:
    async def test_patch_me_updates_profile_fields(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="profileuser",
                email="profile@example.com",
                password="ProfilePass1!",
                display_name="Original Name",
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="profile@example.com", password="ProfilePass1!"),
        )
        token = login_resp.json()["access_token"]

        resp = await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "display_name": "Updated Name",
                "bio": "Local historian",
                "location": "Istanbul, Turkey",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] == "Updated Name"
        assert data["bio"] == "Local historian"
        assert data["location"] == "Istanbul, Turkey"
        assert data["email"] == "profile@example.com"

    async def test_patch_me_allows_clearing_fields(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="clearuser",
                email="clear@example.com",
                password="ClearPass1!",
                display_name="Needs Clearing",
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="clear@example.com", password="ClearPass1!"),
        )
        token = login_resp.json()["access_token"]

        await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "bio": "Has bio",
                "location": "Has location",
            },
        )

        resp = await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "display_name": "   ",
                "bio": "",
                "location": " ",
            },
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["display_name"] is None
        assert data["bio"] is None
        assert data["location"] is None


@pytest.mark.asyncio
class TestAvatarUploadAPI:
    async def test_upload_avatar_returns_avatar_url(self, client, monkeypatch):
        monkeypatch.setattr("app.services.auth_service.upload_bytes", lambda **kwargs: None)

        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="avataruser",
                email="avatar@example.com",
                password="AvatarPass1!",
                display_name="Avatar User",
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="avatar@example.com", password="AvatarPass1!"),
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/me/avatar",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("avatar.png", b"fake-png-bytes", "image/png")},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["avatar_url"] is not None
        assert "/images/users/" in data["avatar_url"]

    async def test_upload_avatar_rejects_unsupported_type(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="badavatar",
                email="badavatar@example.com",
                password="AvatarPass1!",
                display_name="Bad Avatar",
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="badavatar@example.com", password="AvatarPass1!"),
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/me/avatar",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": ("avatar.txt", b"not-an-image", "text/plain")},
        )

        assert resp.status_code == 422


@pytest.mark.asyncio
class TestPasswordChangeAPI:
    async def test_password_change_updates_login_credentials(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="passworduser",
                email="password@example.com",
                password="OldPass1!",
                display_name="Password User",
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="password@example.com", password="OldPass1!"),
        )
        token = login_resp.json()["access_token"]

        change_resp = await client.post(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "OldPass1!",
                "new_password": "NewPass1!",
            },
        )

        assert change_resp.status_code == 204

        old_login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="password@example.com", password="OldPass1!"),
        )
        assert old_login_resp.status_code == 401

        new_login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="password@example.com", password="NewPass1!"),
        )
        assert new_login_resp.status_code == 200

    async def test_password_change_rejects_wrong_current_password(self, client):
        await client.post(
            "/auth/register",
            json=make_user_payload(
                username="wrongcurrent",
                email="wrongcurrent@example.com",
                password="OldPass1!",
                display_name="Wrong Current",
            ),
        )
        login_resp = await client.post(
            "/auth/login",
            json=make_login_payload(email="wrongcurrent@example.com", password="OldPass1!"),
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "WrongPass1!",
                "new_password": "NewPass1!",
            },
        )

        assert resp.status_code == 400


@pytest.mark.asyncio
class TestGoogleOAuthCallbackAPI:
    """API-level tests for OAuth state (CSRF) validation on the callback endpoint."""

    async def test_callback_rejects_missing_state_cookie(self, client):
        resp = await client.get("/auth/google/callback?code=fake-code&state=some-state")
        assert resp.status_code == 400

    async def test_callback_rejects_mismatched_state(self, client):
        resp = await client.get(
            "/auth/google/callback?code=fake-code&state=attacker-state",
            cookies={"oauth_state": "real-state"},
        )
        assert resp.status_code == 400

    async def test_callback_rejects_missing_state_query_param(self, client):
        resp = await client.get(
            "/auth/google/callback?code=fake-code",
            cookies={"oauth_state": "real-state"},
        )
        assert resp.status_code == 422
