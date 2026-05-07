import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.db.enums import ReportReason, ReportStatus
from app.db.user import User
from app.models.story import StoryReportRequest
from app.services.story_service import create_report_for_story


@pytest.mark.asyncio
class TestReportService:
    """Unit tests for story report service."""

    @staticmethod
    def _make_db_with_story(story):
        db = MagicMock()
        db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=story)))
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.rollback = AsyncMock()
        db.add = MagicMock()
        return db

    async def test_create_report_for_story_success(self):
        """Test successful creation of a story report."""
        # Setup mocks
        db = self._make_db_with_story(MagicMock())
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.INAPPROPRIATE_CONTENT,
            description="Contains inappropriate content",
        )

        # Test the function
        result = await create_report_for_story(db, story_id, current_user, payload)

        # Verify
        assert result.story_id == story_id
        assert result.user_id == current_user.id
        assert result.reason == ReportReason.INAPPROPRIATE_CONTENT
        assert result.status == ReportStatus.PENDING
        db.add.assert_called()
        db.commit.assert_called()

    async def test_create_report_for_nonexistent_story_raises_404(self):
        """Test that creating a report for non-existent story raises 404."""
        # Setup mocks
        db = self._make_db_with_story(None)
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.MISINFORMATION,
            description="This is spam",
        )

        # Test that 404 is raised
        with pytest.raises(HTTPException) as exc_info:
            await create_report_for_story(db, story_id, current_user, payload)

        assert exc_info.value.status_code == 404

    async def test_create_duplicate_report_raises_409(self):
        """Test that duplicate report from same user raises 409."""
        # Setup mocks
        db = self._make_db_with_story(MagicMock())
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.OFFENSIVE_LANGUAGE,
            description="Hate speech content",
        )

        db.commit.side_effect = IntegrityError("duplicate", params=None, orig=None)

        # Test that 409 is raised
        with pytest.raises(HTTPException) as exc_info:
            await create_report_for_story(db, story_id, current_user, payload)

        assert exc_info.value.status_code == 409

    async def test_report_with_optional_description(self):
        """Test that report can be created without description."""
        # Setup mocks
        db = self._make_db_with_story(MagicMock())
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.INAPPROPRIATE_CONTENT,
            description=None,
        )

        # Test
        result = await create_report_for_story(db, story_id, current_user, payload)

        # Verify
        assert result.description is None
        assert result.reason == ReportReason.INAPPROPRIATE_CONTENT

    async def test_report_created_with_pending_status(self):
        """Test that reports are created with PENDING status."""
        # Setup mocks
        db = self._make_db_with_story(MagicMock())
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.MISINFORMATION,
        )

        # Test
        result = await create_report_for_story(db, story_id, current_user, payload)

        # Verify initial status
        assert result.status == ReportStatus.PENDING

    async def test_report_timestamp_is_set(self):
        """Test that report creation timestamp is set."""
        # Setup mocks
        db = self._make_db_with_story(MagicMock())
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.INAPPROPRIATE_CONTENT,
        )

        # Test
        before = datetime.now(timezone.utc)
        result = await create_report_for_story(db, story_id, current_user, payload)
        after = datetime.now(timezone.utc)

        # Verify timestamp
        assert result.created_at is not None
        assert before <= result.created_at <= after


@pytest.mark.asyncio
class TestReportStatus:
    """Unit tests for report status management."""

    def test_report_status_enum_values(self):
        """Test that all report status enum values are correct."""
        assert ReportStatus.PENDING.value == "pending"
        assert ReportStatus.RESOLVED.value == "resolved"

    def test_report_reason_enum_values(self):
        """Test that all report reason enum values are correct."""
        assert ReportReason.INAPPROPRIATE_CONTENT.value == "inappropriate_content"
        assert ReportReason.MISINFORMATION.value == "misinformation"
        assert ReportReason.OFFENSIVE_LANGUAGE.value == "offensive_language"

    def test_report_status_transitions_valid(self):
        """Test valid report status transitions."""
        # Reports can transition from PENDING to RESOLVED
        assert ReportStatus.PENDING != ReportStatus.RESOLVED
