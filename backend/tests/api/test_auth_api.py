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
