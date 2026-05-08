import uuid

import pytest
from sqlalchemy import select

from app.db.enums import ReportReason, ReportStatus
from app.db.story import Story
from app.db.story_report import StoryReport


@pytest.mark.asyncio
class TestAdminRemoveStoryAPI:
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

    async def _create_story(self, client, token, title="Story to remove"):
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
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

    async def _report_story(self, client, token, story_id):
        report_resp = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "misinformation", "description": "Misleading"},
        )
        assert report_resp.status_code == 201
        return report_resp.json()["id"]

    async def test_admin_can_soft_delete_story_and_hide_from_public(self, seeded_db, client, db_session):
        author_token = await self._register_and_login(client, "rm_author", "rm_author@example.com", "AuthorPass1!")
        reporter_token = await self._register_and_login(
            client, "rm_reporter", "rm_reporter@example.com", "ReporterPass1!"
        )
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        story_id = await self._create_story(client, author_token, title="Will Be Removed")
        report_id = await self._report_story(client, reporter_token, story_id)

        delete_resp = await client.delete(
            f"/stories/admin/stories/{story_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_resp.status_code == 204

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 404

        list_resp = await client.get("/stories")
        assert list_resp.status_code == 200
        titles = [s["title"] for s in list_resp.json()["stories"]]
        assert "Will Be Removed" not in titles

        report_story_again = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token}"},
            json={"reason": "misinformation", "description": "Should fail"},
        )
        assert report_story_again.status_code == 404

        story_result = await db_session.execute(select(Story).where(Story.id == uuid.UUID(story_id)))
        story = story_result.scalar_one()
        assert story.deleted_at is not None
        assert story.deleted_by is not None

        report_result = await db_session.execute(select(StoryReport).where(StoryReport.id == uuid.UUID(report_id)))
        report = report_result.scalar_one()
        assert report.status == ReportStatus.REMOVED

    async def test_non_admin_cannot_remove_story(self, client):
        author_token = await self._register_and_login(client, "rm_author2", "rm_author2@example.com", "AuthorPass2!")
        user_token = await self._register_and_login(client, "rm_user2", "rm_user2@example.com", "UserPass2!")
        story_id = await self._create_story(client, author_token)

        delete_resp = await client.delete(
            f"/stories/admin/stories/{story_id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )
        assert delete_resp.status_code == 403

    async def test_unauthenticated_user_cannot_remove_story(self, client):
        delete_resp = await client.delete(f"/stories/admin/stories/{uuid.uuid4()}")
        assert delete_resp.status_code == 401

    async def test_remove_nonexistent_story_returns_404_for_admin(self, seeded_db, client):
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        delete_resp = await client.delete(
            f"/stories/admin/stories/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_resp.status_code == 404

    async def test_remove_story_marks_all_pending_reports_removed(self, seeded_db, client, db_session):
        author_token = await self._register_and_login(client, "rm_author3", "rm_author3@example.com", "AuthorPass3!")
        reporter_token_1 = await self._register_and_login(
            client, "rm_reporter3a", "rm_reporter3a@example.com", "ReporterPass3!"
        )
        reporter_token_2 = await self._register_and_login(
            client, "rm_reporter3b", "rm_reporter3b@example.com", "ReporterPass3!"
        )
        admin_token = await self._register_and_login(client, "seed_admin", "seed_admin@example.com", "ValidPass1!")

        story_id = await self._create_story(client, author_token, title="Multi Report Story")
        report_1 = await self._report_story(client, reporter_token_1, story_id)

        report_resp_2 = await client.post(
            f"/stories/{story_id}/report",
            headers={"Authorization": f"Bearer {reporter_token_2}"},
            json={
                "reason": ReportReason.OFFENSIVE_LANGUAGE.value,
                "description": "Second report",
            },
        )
        assert report_resp_2.status_code == 201
        report_2 = report_resp_2.json()["id"]

        delete_resp = await client.delete(
            f"/stories/admin/stories/{story_id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert delete_resp.status_code == 204

        reports_result = await db_session.execute(
            select(StoryReport).where(
                StoryReport.id.in_([uuid.UUID(report_1), uuid.UUID(report_2)]),
            )
        )
        reports = reports_result.scalars().all()

        assert len(reports) == 2
        assert all(report.status == ReportStatus.REMOVED for report in reports)
