import uuid
from datetime import date, datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.db.enums import DatePrecision, ReportStatus, StoryStatus, StoryVisibility
from app.services.admin_service import remove_story_as_admin


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
