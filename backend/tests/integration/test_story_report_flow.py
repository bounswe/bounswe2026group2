import uuid

import pytest

from app.db.enums import ReportReason, ReportStatus


@pytest.mark.asyncio
class TestStoryReportFlow:
    """Test suite for story reporting functionality."""

    async def _register_and_login(self, client, username, email, password):
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
                "title": "Test Story for Reporting",
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

    async def test_authenticated_user_can_report_story(self, client):
        """Test that authenticated user can successfully report a story."""
        author_token = await self._register_and_login(client, "reportauthor", "reportauthor@example.com", "AuthPass1!")
        reporter_token = await self._register_and_login(client, "reporter", "reporter@example.com", "ReporterPass1!")
        story_id = await self._create_story(client, author_token)

        report_resp = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={
                "reason": ReportReason.INAPPROPRIATE_CONTENT.value,
                "description": "This story contains inappropriate content",
            },
        )

        assert report_resp.status_code == 201
        report_data = report_resp.json()
        assert report_data["story_id"] == str(story_id)
        assert report_data["reason"] == ReportReason.INAPPROPRIATE_CONTENT.value
        assert report_data["status"] == ReportStatus.PENDING.value
        assert report_data["description"] == "This story contains inappropriate content"

    async def test_report_story_with_valid_reasons(self, client):
        """Test that reports can be created with all valid reasons."""
        author_token = await self._register_and_login(
            client, "reportauthor2", "reportauthor2@example.com", "AuthPass2!"
        )
        reporter_token = await self._register_and_login(client, "reporter2", "reporter2@example.com", "ReporterPass2!")
        for reason in [r.value for r in ReportReason]:
            story_id = await self._create_story(client, author_token)
            report_resp = await client.post(
                f"/stories/{story_id}/report",
                headers={"Authorization": f"Bearer {reporter_token}"},
                json={"reason": reason, "description": f"Report for {reason}"},
            )
            assert report_resp.status_code == 201

    async def test_duplicate_report_by_same_user_is_rejected(self, client):
        """Test that duplicate reports from the same user are rejected."""
        author_token = await self._register_and_login(
            client, "reportauthor3", "reportauthor3@example.com", "AuthPass3!"
        )
        reporter_token = await self._register_and_login(client, "reporter3", "reporter3@example.com", "ReporterPass3!")
        story_id = await self._create_story(client, author_token)

        # First report should succeed
        first_report = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={
                "reason": ReportReason.MISINFORMATION.value,
                "description": "This is spam",
            },
        )
        assert first_report.status_code == 201

        # Duplicate report should be rejected (409 Conflict)
        duplicate_report = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={
                "reason": ReportReason.MISINFORMATION.value,
                "description": "This is spam again",
            },
        )
        assert duplicate_report.status_code == 409

    async def test_report_nonexistent_story_returns_404(self, client):
        """Test that reporting a non-existent story returns 404."""
        token = await self._register_and_login(client, "reporter4", "reporter4@example.com", "ReporterPass4!")
        nonexistent_story_id = uuid.uuid4()

        report_resp = await client.post(
            f"/stories/{nonexistent_story_id}/report",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "reason": ReportReason.OFFENSIVE_LANGUAGE.value,
                "description": "Report for non-existent story",
            },
        )

        assert report_resp.status_code == 404

    async def test_unauthenticated_user_cannot_report_story(self, client):
        """Test that unauthenticated users cannot report stories."""
        author_token = await self._register_and_login(
            client, "reportauthor5", "reportauthor5@example.com", "AuthPass5!"
        )
        story_id = await self._create_story(client, author_token)

        report_resp = await client.post(
            f"/stories/{story_id}/report",
            json={
                "reason": ReportReason.INAPPROPRIATE_CONTENT.value,
                "description": "Unauthenticated report attempt",
            },
        )

        assert report_resp.status_code == 401

    async def test_report_without_description_is_accepted(self, client):
        """Test that report without description (optional field) is accepted."""
        author_token = await self._register_and_login(
            client, "reportauthor6", "reportauthor6@example.com", "AuthPass6!"
        )
        reporter_token = await self._register_and_login(client, "reporter6", "reporter6@example.com", "ReporterPass6!")
        story_id = await self._create_story(client, author_token)

        report_resp = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={"reason": ReportReason.MISINFORMATION.value},
        )

        assert report_resp.status_code == 201
        assert report_resp.json()["description"] is None

    async def test_report_with_long_description_is_accepted(self, client):
        """Test that reports with long descriptions are accepted."""
        author_token = await self._register_and_login(
            client, "reportauthor7", "reportauthor7@example.com", "AuthPass7!"
        )
        reporter_token = await self._register_and_login(client, "reporter7", "reporter7@example.com", "ReporterPass7!")
        story_id = await self._create_story(client, author_token)

        long_description = "X" * 1000  # Max allowed is 1000 characters

        report_resp = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={
                "reason": ReportReason.INAPPROPRIATE_CONTENT.value,
                "description": long_description,
            },
        )

        assert report_resp.status_code == 201
