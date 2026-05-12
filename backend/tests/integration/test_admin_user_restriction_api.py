import uuid

import pytest
from sqlalchemy import select

from app.db.user import User


@pytest.mark.asyncio
class TestAdminUserRestrictionAPI:
    async def _register_and_login(self, client, username, email, password):
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def _get_user_by_email(self, db_session, email):
        result = await db_session.execute(select(User).where(User.email == email))
        return result.scalar_one()

    async def test_admin_can_restrict_and_unrestrict_user(self, seeded_db, client, db_session):
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")
        await self._register_and_login(client, "restrict_target", "restrict-target@example.com", "TargetPass1!")
        target_user = await self._get_user_by_email(db_session, "restrict-target@example.com")

        restrict_resp = await client.patch(
            f"/admin/users/{target_user.id}/restrict",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert restrict_resp.status_code == 200
        assert restrict_resp.json()["id"] == str(target_user.id)
        assert restrict_resp.json()["is_restricted"] is True

        await db_session.refresh(target_user)
        assert target_user.is_restricted is True

        unrestrict_resp = await client.patch(
            f"/admin/users/{target_user.id}/unrestrict",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert unrestrict_resp.status_code == 200
        assert unrestrict_resp.json()["is_restricted"] is False

        await db_session.refresh(target_user)
        assert target_user.is_restricted is False

    async def test_non_admin_cannot_restrict_user(self, client):
        user_token = await self._register_and_login(client, "regular_mod", "regular-mod@example.com", "RegularPass1!")

        resp = await client.patch(
            f"/admin/users/{uuid.uuid4()}/restrict",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert resp.status_code == 403
        assert "Admin" in resp.json()["detail"]

    async def test_restrict_nonexistent_user_returns_404(self, seeded_db, client):
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        resp = await client.patch(
            f"/admin/users/{uuid.uuid4()}/restrict",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "User not found"
