import pytest
from sqlalchemy import select

from app.db.user import User
from app.models.user import UserLoginRequest, UserRegisterRequest
from app.services.auth_service import login_user, register_user, verify_password


@pytest.mark.asyncio
class TestRegisterAndLoginFlow:
    """Integration test: register a user, then log in. Covers #113."""

    async def test_register_then_login(self, db_session):
        # Register
        reg_payload = UserRegisterRequest(
            username="flowuser",
            email="flow@example.com",
            password="FlowPass1!",
        )
        user_resp = await register_user(db_session, reg_payload)
        assert user_resp.username == "flowuser"
        assert user_resp.email == "flow@example.com"

        # Verify password stored as hash
        result = await db_session.execute(select(User).where(User.email == "flow@example.com"))
        db_user = result.scalar_one()
        assert db_user.password_hash != "FlowPass1!"
        assert verify_password("FlowPass1!", db_user.password_hash) is True

        # Login
        login_payload = UserLoginRequest(email="flow@example.com", password="FlowPass1!")
        token_resp = await login_user(db_session, login_payload)
        assert token_resp.access_token is not None
        assert token_resp.token_type == "bearer"


@pytest.mark.asyncio
class TestDuplicateEmailRejection:
    """Integration test: duplicate email is rejected. Covers #115."""

    async def test_duplicate_email_raises_409(self, db_session):
        payload = UserRegisterRequest(
            username="user1",
            email="dupe@example.com",
            password="ValidPass1!",
        )
        await register_user(db_session, payload)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            payload2 = UserRegisterRequest(
                username="user2",
                email="dupe@example.com",
                password="ValidPass1!",
            )
            await register_user(db_session, payload2)
        assert exc_info.value.status_code == 409
        assert "Email already registered" in exc_info.value.detail

        # Confirm no duplicate user record was created
        from sqlalchemy import func

        count = await db_session.execute(select(func.count()).where(User.email == "dupe@example.com"))
        assert count.scalar_one() == 1


@pytest.mark.asyncio
class TestInvalidCredentialsRejection:
    """Integration test: invalid credentials are rejected. Covers #116."""

    async def test_wrong_password_raises_401(self, db_session):
        payload = UserRegisterRequest(
            username="creduser",
            email="cred@example.com",
            password="ValidPass1!",
        )
        await register_user(db_session, payload)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            login_payload = UserLoginRequest(email="cred@example.com", password="WrongPass1!")
            await login_user(db_session, login_payload)
        assert exc_info.value.status_code == 401

    async def test_nonexistent_email_raises_401(self, db_session):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            login_payload = UserLoginRequest(email="nobody@example.com", password="AnyPass1!")
            await login_user(db_session, login_payload)
        assert exc_info.value.status_code == 401
