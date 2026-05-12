import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.db.enums import DatePrecision, ReportReason, ReportStatus, StoryStatus, StoryVisibility, UserRole
from app.models.admin import UpdateReportStatusRequest
from app.services.admin_service import (
    ensure_admin_user,
    list_admin_reports,
    remove_story_as_admin,
    update_report_status_as_admin,
)


def _make_story(**overrides):
    base = {
        "id": uuid.uuid4(),
        "title": "Story Title",
        "summary": "Story summary",
        "content": "Story content",
        "place_name": "Istanbul",
        "latitude": 41.0082,
        "longitude": 28.9784,
        "date_start": date(1453, 1, 1),
        "date_end": date(1453, 12, 31),
        "date_precision": DatePrecision.YEAR,
        "status": StoryStatus.PUBLISHED,
        "visibility": StoryVisibility.PUBLIC,
        "is_anonymous": False,
        "view_count": 0,
        "created_at": datetime.now(timezone.utc),
        "story_likes": [],
    }
    base.update(overrides)
    return SimpleNamespace(**base)


class TestAdminAuthorization:
    def test_ensure_admin_user_allows_admin(self):
        ensure_admin_user(SimpleNamespace(role=UserRole.ADMIN))

    def test_ensure_admin_user_rejects_non_admin(self):
        with pytest.raises(HTTPException) as exc_info:
            ensure_admin_user(SimpleNamespace(role=UserRole.USER))

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"


@pytest.mark.asyncio
class TestAdminReportsService:
    async def test_list_admin_reports_maps_report_rows(self):
        report_id = uuid.uuid4()
        story_id = uuid.uuid4()
        reporter_id = uuid.uuid4()
        created_at = datetime.now(timezone.utc)
        row = SimpleNamespace(
            id=report_id,
            story_id=story_id,
            user_id=reporter_id,
            reason=ReportReason.INAPPROPRIATE_CONTENT,
            description="bad content",
            status=ReportStatus.PENDING,
            created_at=created_at,
            story_title="Reported Story",
            reporter_username="reporter",
            story_author_username="author",
        )

        db = AsyncMock()
        db.execute.return_value.fetchall = lambda: [row]

        result = await list_admin_reports(db)

        assert result.total == 1
        assert result.reports[0].id == report_id
        assert result.reports[0].story_id == story_id
        assert result.reports[0].user_id == reporter_id
        assert result.reports[0].reason == ReportReason.INAPPROPRIATE_CONTENT
        assert result.reports[0].description == "bad content"
        assert result.reports[0].status == ReportStatus.PENDING
        assert result.reports[0].created_at == created_at
        assert result.reports[0].story_title == "Reported Story"
        assert result.reports[0].reporter_username == "reporter"
        assert result.reports[0].story_author_username == "author"
        db.execute.assert_awaited_once()

    async def test_list_admin_reports_applies_status_filter(self):
        db = AsyncMock()
        db.execute.return_value.fetchall = lambda: []

        await list_admin_reports(db, report_status=ReportStatus.REVIEWED)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "story_reports.status" in sql
        assert "ORDER BY story_reports.created_at DESC" in sql

    async def test_update_report_status_success(self):
        report = SimpleNamespace(
            id=uuid.uuid4(),
            story_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            reason=ReportReason.MISINFORMATION,
            description=None,
            status=ReportStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        payload = UpdateReportStatusRequest(status=ReportStatus.REVIEWED)

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: report))

        result = await update_report_status_as_admin(db, report.id, payload)

        assert report.status == ReportStatus.REVIEWED
        assert result.status == ReportStatus.REVIEWED
        db.add.assert_called_once_with(report)
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(report)

    async def test_update_report_status_raises_404_when_report_missing(self):
        db = AsyncMock()
        db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: None))
        payload = UpdateReportStatusRequest(status=ReportStatus.REVIEWED)

        with pytest.raises(HTTPException) as exc_info:
            await update_report_status_as_admin(db, uuid.uuid4(), payload)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Report not found"
        db.commit.assert_not_awaited()

    async def test_update_report_status_rejects_removed_target_status(self):
        report = SimpleNamespace(status=ReportStatus.PENDING)
        db = AsyncMock()
        db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: report))
        payload = UpdateReportStatusRequest(status=ReportStatus.REMOVED)

        with pytest.raises(HTTPException) as exc_info:
            await update_report_status_as_admin(db, uuid.uuid4(), payload)

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Use the admin remove story endpoint to mark reports as removed"
        db.commit.assert_not_awaited()

    async def test_update_report_status_rejects_removed_report(self):
        report = SimpleNamespace(status=ReportStatus.REMOVED)
        db = AsyncMock()
        db.execute.return_value = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: report))
        payload = UpdateReportStatusRequest(status=ReportStatus.REVIEWED)

        with pytest.raises(HTTPException) as exc_info:
            await update_report_status_as_admin(db, uuid.uuid4(), payload)

        assert exc_info.value.status_code == 409
        assert exc_info.value.detail == "Removed reports cannot be updated"
        db.commit.assert_not_awaited()


@pytest.mark.asyncio
class TestAdminRemoveStoryService:
    async def test_soft_deletes_story_and_marks_pending_reports_removed(self):
        story_id = uuid.uuid4()
        admin_id = uuid.uuid4()
        story = _make_story(id=story_id, deleted_at=None, deleted_by=None)
        current_user = SimpleNamespace(id=admin_id)

        pending_report_1 = SimpleNamespace(status=ReportStatus.PENDING)
        pending_report_2 = SimpleNamespace(status=ReportStatus.PENDING)

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [pending_report_1, pending_report_2])),
        ]

        await remove_story_as_admin(db, story_id, current_user)

        assert story.deleted_at is not None
        assert story.deleted_by == admin_id
        assert pending_report_1.status == ReportStatus.REMOVED
        assert pending_report_2.status == ReportStatus.REMOVED
        db.commit.assert_awaited_once()
        assert db.add.call_count == 3

    async def test_remove_story_raises_404_when_story_missing(self):
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await remove_story_as_admin(db, uuid.uuid4(), SimpleNamespace(id=uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"
        db.commit.assert_not_awaited()
