import uuid
from datetime import datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from starlette.datastructures import Headers, UploadFile

from app.db.enums import MediaType, StoryStatus, StoryVisibility
from app.models.story import MediaUploadRequest, StoryCreateRequest
from app.services.story_service import (
    create_story_with_location,
    get_story_detail_by_id,
    list_available_stories,
    search_available_stories_by_place,
    upload_media_for_story,
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
        "date_start": 1453,
        "date_end": 1453,
        "status": StoryStatus.PUBLISHED,
        "visibility": StoryVisibility.PUBLIC,
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_upload_file(filename: str, content: bytes, content_type: str) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def _make_media_file(**overrides):
    base = {
        "id": uuid.uuid4(),
        "story_id": uuid.uuid4(),
        "bucket_name": "images",
        "storage_key": "stories/key.png",
        "original_filename": "key.png",
        "mime_type": "image/png",
        "media_type": MediaType.IMAGE,
        "file_size_bytes": 1234,
        "sort_order": 0,
        "alt_text": None,
        "caption": None,
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
class TestListAvailableStoriesService:
    async def test_returns_mapped_stories_and_total(self):
        story = _make_story()

        db = AsyncMock()
        db.execute.return_value.all = lambda: [(story, "storyauthor")]

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
        db.execute.return_value.all = lambda: []

        result = await list_available_stories(db)

        assert result.total == 0
        assert result.stories == []
        db.execute.assert_awaited_once()

    async def test_query_contains_expected_filters_and_sorting(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await list_available_stories(db)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "FROM stories" in sql
        assert "JOIN users" in sql
        assert "stories.status" in sql
        assert "stories.visibility" in sql
        assert "ORDER BY stories.created_at DESC" in sql


@pytest.mark.asyncio
class TestSearchAvailableStoriesByPlaceService:
    async def test_returns_matching_stories_and_total(self):
        story = _make_story(place_name="Istanbul, Fatih")

        db = AsyncMock()
        db.execute.return_value.all = lambda: [(story, "storyauthor")]

        result = await search_available_stories_by_place(db, "ist")

        assert result.total == 1
        assert len(result.stories) == 1

        item = result.stories[0]
        assert item.id == story.id
        assert item.title == "Story Title"
        assert item.place_name == "Istanbul, Fatih"
        assert item.author == "storyauthor"

        db.execute.assert_awaited_once()

    async def test_returns_empty_response_when_no_match(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        result = await search_available_stories_by_place(db, "ankara")

        assert result.total == 0
        assert result.stories == []
        db.execute.assert_awaited_once()


@pytest.mark.asyncio
class TestUploadMediaForStoryService:
    async def test_upload_successful(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(
            media_type=MediaType.IMAGE,
            alt_text="an image",
            caption="caption",
            sort_order=2,
        )
        file = _make_upload_file("photo.png", b"fake-image-bytes", "image/png")

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.story_id == story_id
        assert result.media.original_filename == "photo.png"
        assert result.media.mime_type == "image/png"
        assert result.media.media_type == MediaType.IMAGE
        assert result.media.alt_text == "an image"
        assert result.media.caption == "caption"
        assert result.media.sort_order == 2
        assert result.media.file_size_bytes == len(b"fake-image-bytes")
        assert result.media.storage_key.startswith(f"stories/{story_id}/media/")
        assert result.media.storage_key.endswith(".png")

        mock_upload.assert_called_once()
        assert mock_upload.call_args.kwargs["content_type"] == "image/png"
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_upload_rejects_unsupported_mime_type(self):
        payload = MediaUploadRequest(media_type=MediaType.IMAGE)
        file = _make_upload_file("clip.mp4", b"video-bytes", "video/mp4")
        db = AsyncMock()

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            with pytest.raises(HTTPException) as exc_info:
                await upload_media_for_story(db, uuid.uuid4(), file, payload)

        assert exc_info.value.status_code == 422
        mock_upload.assert_not_called()
        db.execute.assert_not_awaited()

    async def test_upload_rejects_empty_file(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.IMAGE)
        file = _make_upload_file("empty.png", b"", "image/png")

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            with pytest.raises(HTTPException) as exc_info:
                await upload_media_for_story(db, story_id, file, payload)

        assert exc_info.value.status_code == 400
        mock_upload.assert_not_called()


@pytest.mark.asyncio
class TestGetStoryDetailByIdService:
    async def test_returns_story_detail_with_media_files(self):
        story_id = uuid.uuid4()
        media_1 = _make_media_file(story_id=story_id, original_filename="photo1.png")
        media_2 = _make_media_file(story_id=story_id, original_filename="photo2.png")
        story = _make_story(id=story_id, media_files=[media_1, media_2])

        db = AsyncMock()
        db.execute.return_value.one_or_none = lambda: (story, "storyauthor")

        result = await get_story_detail_by_id(db, story_id)

        assert result.id == story_id
        assert result.author == "storyauthor"
        assert result.title == "Story Title"
        assert len(result.media_files) == 2
        assert result.media_files[0].original_filename == "photo1.png"
        assert result.media_files[1].original_filename == "photo2.png"
        db.execute.assert_awaited_once()

    async def test_raises_404_when_story_not_found(self):
        db = AsyncMock()
        db.execute.return_value.one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await get_story_detail_by_id(db, uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"


@pytest.mark.asyncio
class TestCreateStoryWithLocationService:
    async def test_create_story_with_valid_location(self):
        payload = StoryCreateRequest(
            title="New Story",
            content="Story content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=1453,
            date_end=1453,
        )
        current_user = SimpleNamespace(id=uuid.uuid4(), username="authoruser")

        db = AsyncMock()
        db.add = MagicMock()

        async def _refresh_side_effect(story_obj):
            story_obj.id = uuid.uuid4()
            story_obj.created_at = datetime.now(timezone.utc)
            story_obj.status = StoryStatus.DRAFT
            story_obj.visibility = StoryVisibility.PRIVATE

        db.refresh.side_effect = _refresh_side_effect

        result = await create_story_with_location(db, current_user, payload)

        assert result.title == "New Story"
        assert result.author == "authoruser"
        assert result.place_name == "Istanbul"
        assert result.latitude == 41.0082
        assert result.longitude == 28.9784
        assert result.media_files == []
        db.add.assert_called_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_create_story_rejects_missing_place_name(self):
        payload = StoryCreateRequest(
            title="New Story",
            content="Story content",
            summary="Summary",
            place_name="   ",
            latitude=41.0082,
            longitude=28.9784,
        )
        current_user = SimpleNamespace(id=uuid.uuid4(), username="authoruser")
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await create_story_with_location(db, current_user, payload)

        assert exc_info.value.status_code == 422
        assert "place_name is required" in exc_info.value.detail
        db.add.assert_not_called()
