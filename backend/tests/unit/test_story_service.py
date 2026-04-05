import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.db.enums import StoryStatus, StoryVisibility
from app.services.story_service import list_available_stories


def _make_story(**overrides):
    base = {
        "id": uuid.uuid4(),
        "title": "Story Title",
        "summary": "Story summary",
        "content": "Story content",
        "place_name": "Istanbul",
        "latitude": 41.0082,
        "longitude": 28.9784,
        "date_start": 1453,
        "date_end": 1453,
        "status": StoryStatus.PUBLISHED,
        "visibility": StoryVisibility.PUBLIC,
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
class TestListAvailableStoriesService:
    async def test_returns_mapped_stories_and_total(self):
        story = _make_story()

        db = AsyncMock()
        db.execute.return_value.all.return_value = [(story, "storyauthor")]

        result = await list_available_stories(db)

        assert result.total == 1
        assert len(result.stories) == 1

        item = result.stories[0]
        assert item.id == story.id
        assert item.title == "Story Title"
        assert item.summary == "Story summary"
        assert item.content == "Story content"
        assert item.author == "storyauthor"
        assert item.place_name == "Istanbul"
        assert item.latitude == 41.0082
        assert item.longitude == 28.9784
        assert item.date_start == 1453
        assert item.date_end == 1453
        assert item.date_label == "1453 - 1453"
        assert item.status == StoryStatus.PUBLISHED
        assert item.visibility == StoryVisibility.PUBLIC
        assert item.created_at == story.created_at

        db.execute.assert_awaited_once()

    async def test_returns_empty_response_when_no_rows(self):
        db = AsyncMock()
        db.execute.return_value.all.return_value = []

        result = await list_available_stories(db)

        assert result.total == 0
        assert result.stories == []
        db.execute.assert_awaited_once()

    async def test_query_contains_expected_filters_and_sorting(self):
        db = AsyncMock()
        db.execute.return_value.all.return_value = []

        await list_available_stories(db)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "FROM stories" in sql
        assert "JOIN users" in sql
        assert "stories.status" in sql
        assert "stories.visibility" in sql
        assert "ORDER BY stories.created_at DESC" in sql
