import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.db.enums import ReportReason, ReportStatus
from app.db.user import User
from app.models.story import StoryReportRequest
from app.services.story_service import create_report_for_story


@pytest.mark.asyncio
class TestReportService:
    """Unit tests for story report service."""

    async def test_create_report_for_story_success(self):
        """Test successful creation of a story report."""
        # Setup mocks
        db = AsyncMock()
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.INAPPROPRIATE,
            description="Contains inappropriate content",
        )

        # Mock the story existence check
        db.execute = AsyncMock()
        db.execute.return_value.scalars.return_value.first.return_value = MagicMock()

        # Test the function
        result = await create_report_for_story(db, story_id, current_user, payload)

        # Verify
        assert result.story_id == story_id
        assert result.user_id == current_user.id
        assert result.reason == ReportReason.INAPPROPRIATE
        assert result.status == ReportStatus.PENDING
        db.add.assert_called()
        db.commit.assert_called()

    async def test_create_report_for_nonexistent_story_raises_404(self):
        """Test that creating a report for non-existent story raises 404."""
        # Setup mocks
        db = AsyncMock()
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.SPAM,
            description="This is spam",
        )

        # Mock story not found
        db.execute = AsyncMock()
        db.execute.return_value.scalars.return_value.first.return_value = None

        # Test that 404 is raised
        with pytest.raises(HTTPException) as exc_info:
            await create_report_for_story(db, story_id, current_user, payload)

        assert exc_info.value.status_code == 404

    async def test_create_duplicate_report_raises_409(self):
        """Test that duplicate report from same user raises 409."""
        # Setup mocks
        db = AsyncMock()
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.HATE_SPEECH,
            description="Hate speech content",
        )

        # Mock story exists
        db.execute = AsyncMock()
        db.execute.return_value.scalars.return_value.first.return_value = MagicMock()

        # Mock duplicate report check - query returns existing report
        db.query = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = MagicMock()
        db.query.return_value = mock_query

        # Test that 409 is raised
        with pytest.raises(HTTPException) as exc_info:
            await create_report_for_story(db, story_id, current_user, payload)

        assert exc_info.value.status_code == 409

    async def test_report_with_optional_description(self):
        """Test that report can be created without description."""
        # Setup mocks
        db = AsyncMock()
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.INAPPROPRIATE,
            description=None,
        )

        # Mock story exists
        db.execute = AsyncMock()
        db.execute.return_value.scalars.return_value.first.return_value = MagicMock()

        # Mock no duplicate
        db.query = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        db.query.return_value = mock_query

        # Test
        result = await create_report_for_story(db, story_id, current_user, payload)

        # Verify
        assert result.description is None
        assert result.reason == ReportReason.INAPPROPRIATE

    async def test_report_created_with_pending_status(self):
        """Test that reports are created with PENDING status."""
        # Setup mocks
        db = AsyncMock()
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.SPAM,
        )

        # Mock story exists
        db.execute = AsyncMock()
        db.execute.return_value.scalars.return_value.first.return_value = MagicMock()

        # Mock no duplicate
        db.query = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        db.query.return_value = mock_query

        # Test
        result = await create_report_for_story(db, story_id, current_user, payload)

        # Verify initial status
        assert result.status == ReportStatus.PENDING

    async def test_report_timestamp_is_set(self):
        """Test that report creation timestamp is set."""
        # Setup mocks
        db = AsyncMock()
        current_user = MagicMock(spec=User)
        current_user.id = uuid.uuid4()

        story_id = uuid.uuid4()
        payload = StoryReportRequest(
            reason=ReportReason.INAPPROPRIATE,
        )

        # Mock story exists
        db.execute = AsyncMock()
        db.execute.return_value.scalars.return_value.first.return_value = MagicMock()

        # Mock no duplicate
        db.query = MagicMock()
        mock_query = MagicMock()
        mock_query.filter.return_value.first.return_value = None
        db.query.return_value = mock_query

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
        assert ReportStatus.REVIEWED.value == "reviewed"
        assert ReportStatus.RESOLVED.value == "resolved"

    def test_report_reason_enum_values(self):
        """Test that all report reason enum values are correct."""
        assert ReportReason.INAPPROPRIATE.value == "inappropriate"
        assert ReportReason.SPAM.value == "spam"
        assert ReportReason.HATE_SPEECH.value == "hate_speech"
        assert ReportReason.MISINFORMATION.value == "misinformation"
        assert ReportReason.COPYRIGHT_VIOLATION.value == "copyright_violation"
        assert ReportReason.OTHER.value == "other"

    def test_report_status_transitions_valid(self):
        """Test valid report status transitions."""
        # Reports can transition from PENDING to REVIEWED or RESOLVED
        assert ReportStatus.PENDING != ReportStatus.REVIEWED
        assert ReportStatus.PENDING != ReportStatus.RESOLVED
        assert ReportStatus.REVIEWED != ReportStatus.RESOLVED
