import uuid

import pytest

from app.db.enums import ReportReason, ReportStatus, UserRole


@pytest.mark.asyncio
class TestAdminReportsAPI:
    """Test suite for admin reports API endpoints."""

    async def _register_and_login(self, client, username, email, password, role=UserRole.USER):
        """Helper to register and login a user."""
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def _create_story(self, client, token):
        """Helper to create a story."""
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Test Story for Admin Review",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
                "date_end": 1453,
            },
        )
        assert create_resp.status_code == 201
        return create_resp.json()["id"]

    async def _create_report(self, client, token, story_id):
        """Helper to create a report."""
        report_resp = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": ReportReason.INAPPROPRIATE_CONTENT.value,
                "description": "Inappropriate content",
            },
        )
        assert report_resp.status_code == 201
        return report_resp.json()["id"]

    async def test_admin_can_view_all_reports(self, seeded_db, client):
        """Test that admin user can view all reports."""
        author_token = await self._register_and_login(client, "author", "author@example.com", "AuthPass1!")
        reporter_token = await self._register_and_login(client, "reporter", "reporter@example.com", "ReporterPass1!")

        # Create multiple reports
        story_id_1 = await self._create_story(client, author_token)
        story_id_2 = await self._create_story(client, author_token)

        await self._create_report(client, reporter_token, story_id_1)
        await self._create_report(client, reporter_token, story_id_2)

        # Admin should be able to view reports
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")
        list_resp = await client.get(
            "/stories/admin/reports",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert list_resp.status_code == 200

    async def test_non_admin_cannot_access_admin_reports(self, client):
        """Test that non-admin users get 403 when accessing admin reports."""
        user_token = await self._register_and_login(client, "regularuser", "regularuser@example.com", "UserPass1!")

        list_resp = await client.get(
            "/stories/admin/reports",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert list_resp.status_code == 403
        assert "Admin" in list_resp.json()["detail"]

    async def test_unauthenticated_user_cannot_access_admin_reports(self, client):
        """Test that unauthenticated users get 401 when accessing admin reports."""
        list_resp = await client.get("/stories/admin/reports")

        assert list_resp.status_code == 401

    async def test_admin_can_filter_reports_by_status(self, seeded_db, client):
        """Test that admin can filter reports by status."""
        author_token = await self._register_and_login(client, "author2", "author2@example.com", "AuthPass2!")
        reporter_token = await self._register_and_login(client, "reporter2", "reporter2@example.com", "ReporterPass2!")
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        # Create a report
        story_id = await self._create_story(client, author_token)
        await self._create_report(client, reporter_token, story_id)

        # Try to filter by status (should work if user is admin)
        filter_resp = await client.get(
            f"/stories/admin/reports?status={ReportStatus.PENDING.value}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert filter_resp.status_code == 200
        data = filter_resp.json()
        assert data["total"] == 1
        assert data["reports"][0]["status"] == ReportStatus.PENDING.value

    async def test_admin_can_update_report_status(self, seeded_db, client):
        """Test that admin can update report status."""
        author_token = await self._register_and_login(client, "author3", "author3@example.com", "AuthPass3!")
        reporter_token = await self._register_and_login(client, "reporter3", "reporter3@example.com", "ReporterPass3!")
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        # Create a report
        story_id = await self._create_story(client, author_token)
        report_id = await self._create_report(client, reporter_token, story_id)

        # Try to update status (should work if user is admin)
        update_resp = await client.put(
            f"/stories/admin/reports/{report_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": ReportStatus.RESOLVED.value},
        )

        assert update_resp.status_code == 200
        assert update_resp.json()["status"] == ReportStatus.RESOLVED.value

    async def test_non_admin_cannot_update_report_status(self, client):
        """Test that non-admin users get 403 when updating report status."""
        user_token = await self._register_and_login(client, "regularuser2", "regularuser2@example.com", "UserPass2!")
        report_id = uuid.uuid4()

        update_resp = await client.put(
            f"/stories/admin/reports/{report_id}",
            headers={"Authorization": f"Bearer {user_token}"},
            json={"status": ReportStatus.RESOLVED.value},
        )

        assert update_resp.status_code == 403
        assert "Admin" in update_resp.json()["detail"]

    async def test_update_nonexistent_report_returns_404(self, seeded_db, client):
        """Test that updating a non-existent report returns 404."""
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")
        nonexistent_report_id = uuid.uuid4()

        update_resp = await client.put(
            f"/stories/admin/reports/{nonexistent_report_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"status": ReportStatus.RESOLVED.value},
        )

        assert update_resp.status_code == 404

    async def test_admin_reports_response_includes_report_details(self, seeded_db, client):
        """Test that admin reports listing includes all necessary report details."""
        author_token = await self._register_and_login(client, "author4", "author4@example.com", "AuthPass4!")
        reporter_token = await self._register_and_login(client, "reporter4", "reporter4@example.com", "ReporterPass4!")
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        # Create a report
        story_id = await self._create_story(client, author_token)
        await self._create_report(client, reporter_token, story_id)

        # Get reports as admin
        list_resp = await client.get(
            "/stories/admin/reports",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert list_resp.status_code == 200
        data = list_resp.json()
        assert "total" in data
        assert "reports" in data
        assert isinstance(data["reports"], list)

        # Check report contains expected fields
        if data["reports"]:
            report = data["reports"][0]
            assert "id" in report
            assert "story_id" in report
            assert "user_id" in report
            assert "reason" in report
            assert "status" in report
            assert "created_at" in report
            assert "story_title" in report
            assert "story_author_username" in report
            assert "reporter_username" in report
            assert report["story_title"] == "Test Story for Admin Review"
            assert report["story_author_username"] == "author4"
            assert report["reporter_username"] == "reporter4"
