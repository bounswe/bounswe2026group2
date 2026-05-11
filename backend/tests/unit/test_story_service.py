import uuid
from datetime import date, datetime, timezone
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.datastructures import Headers, UploadFile

from app.db.enums import (
    DatePrecision,
    MediaType,
    NotificationEventType,
    ReportStatus,
    StoryStatus,
    StoryVisibility,
)
from app.db.notification import Notification
from app.db.tag import Tag
from app.models.comment import CommentCreateRequest
from app.models.story import MediaUploadRequest, StoryCreateRequest, StoryResponse, StoryUpdateRequest
from app.services.story_service import (
    create_comment_for_story,
    create_story_with_location,
    delete_comment_for_story,
    get_nearby_stories,
    get_story_detail_by_id,
    get_story_like_summary,
    get_timeline_stories,
    like_story,
    list_available_stories,
    list_comments_for_story,
    list_saved_stories_for_user,
    remove_story_as_admin,
    save_story_for_user,
    search_available_stories_by_place,
    unlike_story,
    unsave_story_for_user,
    update_story_with_location_and_dates,
    upload_media_for_story,
)
from app.services.tag_service import (
    apply_ai_tags_to_story,
    attach_tags_to_story,
    build_tag_slug,
    get_or_create_tags,
    normalize_tag_list,
    normalize_tag_name,
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
        "created_at": datetime.now(timezone.utc),
        "story_likes": [],
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
        "transcript": None,
        "created_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_user(**overrides):
    base = {
        "id": uuid.uuid4(),
        "username": "storyauthor",
        "display_name": "Story Author",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _make_comment(**overrides):
    base = {
        "id": uuid.uuid4(),
        "story_id": uuid.uuid4(),
        "user_id": uuid.uuid4(),
        "content": "Comment content",
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
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
        assert item.date_start == date(1453, 1, 1)
        assert item.date_end == date(1453, 12, 31)
        assert item.date_label == "1453"
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

    async def test_query_includes_bounds_filters_when_provided(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await list_available_stories(
            db,
            min_lat=40.9,
            max_lat=41.1,
            min_lng=28.8,
            max_lng=29.1,
        )

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "stories.latitude IS NOT NULL" in sql
        assert "stories.longitude IS NOT NULL" in sql
        assert "stories.latitude >=" in sql
        assert "stories.latitude <=" in sql
        assert "stories.longitude >=" in sql
        assert "stories.longitude <=" in sql

    async def test_query_includes_date_overlap_filters_when_query_range_provided(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await list_available_stories(
            db,
            query_start=date(2025, 8, 1),
            query_end=date(2025, 8, 31),
        )

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "stories.date_start IS NOT NULL" in sql
        assert "stories.date_end IS NOT NULL" in sql
        assert "stories.date_start <=" in sql
        assert "stories.date_end >=" in sql

    async def test_query_includes_tag_or_filter_and_relevance_sorting_when_tags_provided(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await list_available_stories(db, tags=[" Spor ", "history", "spor"])

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "JOIN story_tags" in sql
        assert "JOIN tags" in sql
        assert "tags.name IN" in sql
        assert "GROUP BY stories.id, users.username" in sql
        assert "ORDER BY count(tags.id) DESC, stories.created_at DESC" in sql


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

    async def test_search_query_includes_date_overlap_filters(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await search_available_stories_by_place(
            db,
            "ankara",
            query_start=date(1900, 1, 1),
            query_end=date(1950, 12, 31),
        )

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "stories.date_start <=" in sql
        assert "stories.date_end >=" in sql

    async def test_general_search_query_includes_story_text_place_and_tag_matching(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await search_available_stories_by_place(db, search_query="gecek")

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "LEFT OUTER JOIN story_tags" in sql
        assert "LEFT OUTER JOIN tags" in sql
        assert "stories.title" in sql
        assert "stories.summary" in sql
        assert "stories.content" in sql
        assert "stories.place_name" in sql
        assert "tags.name" in sql
        assert "GROUP BY stories.id, users.username" in sql
        assert "ORDER BY" in sql
        assert "stories.created_at DESC" in sql

    async def test_search_query_includes_tag_or_filter_and_relevance_sorting_when_tags_provided(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await search_available_stories_by_place(db, "istanbul", tags=["spor", "history"])

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "stories.place_name" in sql
        assert "JOIN story_tags" in sql
        assert "JOIN tags" in sql
        assert "tags.name IN" in sql
        assert "GROUP BY stories.id, users.username" in sql
        assert "ORDER BY count(tags.id) DESC, stories.created_at DESC" in sql

    async def test_search_rejects_blank_tag_without_querying_db(self):
        db = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await search_available_stories_by_place(db, "istanbul", tags=[" "])

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "Tags cannot be blank"
        db.execute.assert_not_awaited()


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

    async def test_upload_accepts_audio_webm(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("recording.webm", b"audio-bytes", "audio/webm;codecs=opus")
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.mime_type == "audio/webm"
        assert result.media.media_type == MediaType.AUDIO

    async def test_upload_audio_queues_background_transcription(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("recording.webm", b"audio-bytes", "audio/webm")
        background_tasks = BackgroundTasks()

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(
                db,
                story_id,
                file,
                payload,
                background_tasks=background_tasks,
            )

        assert result.media.media_type == MediaType.AUDIO
        assert len(background_tasks.tasks) == 1
        task = background_tasks.tasks[0]
        assert task.func.__name__ == "transcribe_media_file"
        assert task.kwargs["media_file_id"] == result.media.id
        assert task.kwargs["filename"] == "recording.webm"
        assert task.kwargs["content"] == b"audio-bytes"
        assert task.kwargs["mime_type"] == "audio/webm"

    async def test_upload_audio_with_transcript_persists_and_skips_background_transcription(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO, transcript="  Reviewed transcript  ")
        file = _make_upload_file("recording.webm", b"audio-bytes", "audio/webm")
        background_tasks = BackgroundTasks()

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(
                db,
                story_id,
                file,
                payload,
                background_tasks=background_tasks,
            )

        assert result.media.media_type == MediaType.AUDIO
        assert result.media.transcript == "Reviewed transcript"
        assert background_tasks.tasks == []

    async def test_upload_audio_with_blank_transcript_queues_background_transcription(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO, transcript="   ")
        file = _make_upload_file("recording.webm", b"audio-bytes", "audio/webm")
        background_tasks = BackgroundTasks()

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(
                db,
                story_id,
                file,
                payload,
                background_tasks=background_tasks,
            )

        assert result.media.transcript is None
        assert len(background_tasks.tasks) == 1

    async def test_upload_image_does_not_queue_background_transcription(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.IMAGE)
        file = _make_upload_file("photo.png", b"fake-image-bytes", "image/png")
        background_tasks = BackgroundTasks()

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            await upload_media_for_story(
                db,
                story_id,
                file,
                payload,
                background_tasks=background_tasks,
            )

        assert background_tasks.tasks == []

    async def test_upload_accepts_audio_webm_mixed_case(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("recording.webm", b"audio-bytes", "Audio/WebM;codecs=opus")
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.media_type == MediaType.AUDIO

    async def test_upload_accepts_audio_x_m4a_alias(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("recording.m4a", b"audio-bytes", "audio/x-m4a")
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.mime_type == "audio/mp4"
        assert result.media.media_type == MediaType.AUDIO

    async def test_upload_accepts_audio_octet_stream_when_extension_is_m4a(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("recording.m4a", b"audio-bytes", "application/octet-stream")
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.mime_type == "audio/mp4"
        assert mock_upload.call_args.kwargs["content_type"] == "audio/mp4"

    async def test_upload_rejects_audio_octet_stream_without_supported_extension(self):
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("recording.bin", b"audio-bytes", "application/octet-stream")
        db = AsyncMock()

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            with pytest.raises(HTTPException) as exc_info:
                await upload_media_for_story(db, uuid.uuid4(), file, payload)

        assert exc_info.value.status_code == 422
        assert "application/octet-stream" in exc_info.value.detail
        mock_upload.assert_not_called()

    async def test_upload_accepts_video_webm(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.VIDEO)
        file = _make_upload_file("recording.webm", b"video-bytes", "video/webm;codecs=vp8,opus")
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.mime_type == "video/webm"
        assert result.media.media_type == MediaType.VIDEO

    async def test_upload_accepts_video_webm_mixed_case(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        payload = MediaUploadRequest(media_type=MediaType.VIDEO)
        file = _make_upload_file("recording.webm", b"video-bytes", "Video/WebM;codecs=vp9")
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(media_obj):
            media_obj.id = uuid.uuid4()
            media_obj.created_at = datetime.now(timezone.utc)

        db.refresh.side_effect = _refresh_side_effect

        with patch("app.services.story_service.upload_bytes"):
            result = await upload_media_for_story(db, story_id, file, payload)

        assert result.media.media_type == MediaType.VIDEO

    async def test_upload_rejects_video_webm_as_wrong_media_type(self):
        payload = MediaUploadRequest(media_type=MediaType.AUDIO)
        file = _make_upload_file("clip.webm", b"video-bytes", "video/webm;codecs=vp8,opus")
        db = AsyncMock()

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            with pytest.raises(HTTPException) as exc_info:
                await upload_media_for_story(db, uuid.uuid4(), file, payload)

        assert exc_info.value.status_code == 422
        assert "video/webm" in exc_info.value.detail
        mock_upload.assert_not_called()

    async def test_upload_strips_mime_params_for_validation(self):
        payload = MediaUploadRequest(media_type=MediaType.IMAGE)
        file = _make_upload_file("clip.webm", b"audio-bytes", "audio/webm;codecs=opus")
        db = AsyncMock()

        with patch("app.services.story_service.upload_bytes") as mock_upload:
            with pytest.raises(HTTPException) as exc_info:
                await upload_media_for_story(db, uuid.uuid4(), file, payload)

        assert exc_info.value.status_code == 422
        assert "audio/webm" in exc_info.value.detail
        mock_upload.assert_not_called()

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
        db.execute.side_effect = [
            SimpleNamespace(one_or_none=lambda: (story, "storyauthor")),
            SimpleNamespace(scalar_one=lambda: 2),
        ]

        result = await get_story_detail_by_id(db, story_id)

        assert result.id == story_id
        assert result.author == "storyauthor"
        assert result.title == "Story Title"
        assert len(result.media_files) == 2
        assert result.media_files[0].original_filename == "photo1.png"
        assert result.media_files[1].original_filename == "photo2.png"
        assert result.media_files[0].media_url.endswith("/images/stories/key.png")
        assert result.media_files[1].media_url.endswith("/images/stories/key.png")
        assert result.like_count == 2
        assert db.execute.await_count == 2

    async def test_raises_404_when_story_not_found(self):
        db = AsyncMock()
        db.execute.return_value.one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await get_story_detail_by_id(db, uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"


@pytest.mark.asyncio
class TestStorySaveService:
    async def test_save_story_creates_save_and_returns_saved_true(self):
        story_id = uuid.uuid4()
        current_user = _make_user()
        story = _make_story(id=story_id, user_id=uuid.uuid4())
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
        ]

        result = await save_story_for_user(db, story_id, current_user)

        assert result.story_id == story_id
        assert result.saved is True
        assert db.add.call_count == 2
        added_save = db.add.call_args_list[0].args[0]
        assert added_save.story_id == story_id
        assert added_save.user_id == current_user.id
        added_notification = db.add.call_args_list[1].args[0]
        assert isinstance(added_notification, Notification)
        assert added_notification.recipient_user_id == story.user_id
        assert added_notification.actor_user_id == current_user.id
        assert added_notification.story_id == story_id
        assert added_notification.event_type == NotificationEventType.STORY_BOOKMARKED
        db.commit.assert_awaited_once()

    async def test_save_story_is_idempotent_when_already_saved(self):
        story_id = uuid.uuid4()
        current_user = _make_user()
        story = _make_story(id=story_id, user_id=uuid.uuid4())
        existing_save = SimpleNamespace(id=uuid.uuid4(), story_id=story_id, user_id=current_user.id)
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: existing_save),
        ]

        result = await save_story_for_user(db, story_id, current_user)

        assert result.saved is True
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_save_story_raises_404_when_story_missing(self):
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await save_story_for_user(db, uuid.uuid4(), _make_user())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"

    async def test_unsave_story_deletes_save_when_present(self):
        story_id = uuid.uuid4()
        current_user = _make_user()
        story = _make_story(id=story_id)
        existing_save = SimpleNamespace(id=uuid.uuid4(), story_id=story_id, user_id=current_user.id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: existing_save),
        ]

        result = await unsave_story_for_user(db, story_id, current_user)

        assert result.story_id == story_id
        assert result.saved is False
        db.delete.assert_awaited_once_with(existing_save)
        db.commit.assert_awaited_once()

    async def test_unsave_story_is_idempotent_when_not_saved(self):
        story_id = uuid.uuid4()
        current_user = _make_user()
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
        ]

        result = await unsave_story_for_user(db, story_id, current_user)

        assert result.saved is False
        db.delete.assert_not_awaited()
        db.commit.assert_not_awaited()

    async def test_list_saved_stories_returns_story_list(self):
        current_user = _make_user()
        saved_story = _make_story()
        db = AsyncMock()
        db.execute.return_value.all = lambda: [(saved_story, "storyauthor")]

        result = await list_saved_stories_for_user(db, current_user)

        assert result.total == 1
        assert len(result.stories) == 1
        assert result.stories[0].id == saved_story.id
        assert result.stories[0].author == "storyauthor"

    async def test_list_saved_stories_query_filters_to_public_published(self):
        current_user = _make_user()
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await list_saved_stories_for_user(db, current_user)

        stmt = db.execute.await_args.args[0]
        where_clause = str(stmt.whereclause)
        assert "story_saves.user_id" in where_clause
        assert "stories.status" in where_clause
        assert "stories.visibility" in where_clause


@pytest.mark.asyncio
class TestStoryCommentService:
    async def test_list_comments_returns_comments_in_order(self):
        story_id = uuid.uuid4()
        first_author = _make_user()
        second_author = _make_user(username="otherauthor", display_name="Other Author")
        first_comment = _make_comment(story_id=story_id, content="First")
        second_comment = _make_comment(story_id=story_id, content="Second")

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: _make_story(id=story_id)),
            SimpleNamespace(all=lambda: [(first_comment, first_author), (second_comment, second_author)]),
        ]

        result = await list_comments_for_story(db, story_id)

        assert result.total == 2
        assert [comment.content for comment in result.comments] == ["First", "Second"]
        assert result.comments[0].author.username == "storyauthor"
        assert result.comments[1].author.username == "otherauthor"

    async def test_list_comments_raises_404_when_story_missing(self):
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await list_comments_for_story(db, uuid.uuid4())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"

    async def test_create_comment_success(self):
        story_id = uuid.uuid4()
        current_user = _make_user()
        payload = CommentCreateRequest(content="  New comment  ")
        story = _make_story(id=story_id, user_id=uuid.uuid4())

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        async def _refresh_side_effect(comment_obj):
            comment_obj.id = uuid.uuid4()
            comment_obj.created_at = datetime.now(timezone.utc)
            comment_obj.updated_at = datetime.now(timezone.utc)

        async def _flush_side_effect():
            comment_obj = db.add.call_args_list[0].args[0]
            comment_obj.id = uuid.uuid4()

        db.flush.side_effect = _flush_side_effect
        db.refresh.side_effect = _refresh_side_effect

        result = await create_comment_for_story(db, story_id, current_user, payload)

        assert result.story_id == story_id
        assert result.content == "New comment"
        assert result.author.username == "storyauthor"
        assert db.add.call_count == 2
        added_notification = db.add.call_args_list[1].args[0]
        assert isinstance(added_notification, Notification)
        assert added_notification.recipient_user_id == story.user_id
        assert added_notification.actor_user_id == current_user.id
        assert added_notification.story_id == story_id
        assert added_notification.event_type == NotificationEventType.STORY_COMMENTED
        assert added_notification.comment_id is not None
        db.flush.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once()

    async def test_create_comment_raises_404_when_story_missing(self):
        current_user = _make_user()
        payload = CommentCreateRequest(content="Hello")
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await create_comment_for_story(db, uuid.uuid4(), current_user, payload)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"

    async def test_delete_comment_success_for_owner(self):
        story_id = uuid.uuid4()
        comment_id = uuid.uuid4()
        current_user = _make_user()
        comment = _make_comment(id=comment_id, story_id=story_id, user_id=current_user.id)
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: comment),
        ]

        await delete_comment_for_story(db, story_id, comment_id, current_user)

        db.delete.assert_awaited_once_with(comment)
        db.commit.assert_awaited_once()

    async def test_delete_comment_raises_403_for_non_owner(self):
        story_id = uuid.uuid4()
        comment_id = uuid.uuid4()
        current_user = _make_user()
        comment = _make_comment(id=comment_id, story_id=story_id, user_id=uuid.uuid4())
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: comment),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await delete_comment_for_story(db, story_id, comment_id, current_user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Not allowed to delete this comment"
        db.delete.assert_not_awaited()

    async def test_delete_comment_raises_404_when_comment_missing(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
        ]

        with pytest.raises(HTTPException) as exc_info:
            await delete_comment_for_story(db, story_id, uuid.uuid4(), _make_user())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Comment not found"

    async def test_delete_comment_raises_404_when_story_missing(self):
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await delete_comment_for_story(db, uuid.uuid4(), uuid.uuid4(), _make_user())

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"


@pytest.mark.asyncio
class TestStoryLikeService:
    async def test_get_story_like_summary_returns_unliked_state(self):
        story_id = uuid.uuid4()
        current_user = SimpleNamespace(id=uuid.uuid4())
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        result = await get_story_like_summary(db, story_id, current_user)

        assert result.story_id == story_id
        assert result.liked is False
        assert result.like_count == 0

    async def test_get_story_like_summary_returns_liked_state(self):
        story_id = uuid.uuid4()
        current_user = SimpleNamespace(id=uuid.uuid4())
        story = _make_story(id=story_id)
        existing_like = SimpleNamespace(id=uuid.uuid4(), story_id=story_id, user_id=current_user.id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: existing_like),
            SimpleNamespace(scalar_one=lambda: 2),
        ]

        result = await get_story_like_summary(db, story_id, current_user)

        assert result.story_id == story_id
        assert result.liked is True
        assert result.like_count == 2

    async def test_like_story_creates_like_and_returns_count(self):
        story_id = uuid.uuid4()
        current_user = SimpleNamespace(id=uuid.uuid4())
        story = _make_story(id=story_id, user_id=uuid.uuid4())
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: SimpleNamespace(user_id=current_user.id)),
            SimpleNamespace(scalar_one=lambda: 1),
        ]

        result = await like_story(db, story_id, current_user)

        assert result.story_id == story_id
        assert result.liked is True
        assert result.like_count == 1
        db.commit.assert_awaited_once()
        assert db.add.call_count == 2
        added_like = db.add.call_args_list[0].args[0]
        assert added_like.story_id == story_id
        assert added_like.user_id == current_user.id
        added_notification = db.add.call_args_list[1].args[0]
        assert isinstance(added_notification, Notification)
        assert added_notification.recipient_user_id == story.user_id
        assert added_notification.actor_user_id == current_user.id
        assert added_notification.story_id == story_id
        assert added_notification.event_type == NotificationEventType.STORY_LIKED

    async def test_like_story_is_idempotent_when_like_exists(self):
        story_id = uuid.uuid4()
        current_user = SimpleNamespace(id=uuid.uuid4())
        story = _make_story(id=story_id, user_id=uuid.uuid4())
        existing_like = SimpleNamespace(id=uuid.uuid4(), story_id=story_id, user_id=current_user.id)
        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: existing_like),
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: existing_like),
            SimpleNamespace(scalar_one=lambda: 1),
        ]

        result = await like_story(db, story_id, current_user)

        assert result.liked is True
        assert result.like_count == 1
        db.add.assert_not_called()
        db.commit.assert_not_awaited()

    async def test_like_story_raises_404_when_story_missing(self):
        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await like_story(db, uuid.uuid4(), SimpleNamespace(id=uuid.uuid4()))

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"

    async def test_unlike_story_deletes_like_and_returns_zero_count(self):
        story_id = uuid.uuid4()
        current_user = SimpleNamespace(id=uuid.uuid4())
        existing_like = SimpleNamespace(id=uuid.uuid4(), story_id=story_id, user_id=current_user.id)
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: existing_like),
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        result = await unlike_story(db, story_id, current_user)

        assert result.story_id == story_id
        assert result.liked is False
        assert result.like_count == 0
        db.delete.assert_awaited_once_with(existing_like)
        db.commit.assert_awaited_once()

    async def test_unlike_story_is_idempotent_when_like_missing(self):
        story_id = uuid.uuid4()
        current_user = SimpleNamespace(id=uuid.uuid4())
        story = _make_story(id=story_id)
        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(scalar_one_or_none=lambda: None),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        result = await unlike_story(db, story_id, current_user)

        assert result.liked is False
        assert result.like_count == 0
        db.delete.assert_not_awaited()
        db.commit.assert_not_awaited()


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

        mock_story = SimpleNamespace(
            id=uuid.uuid4(),
            title="New Story",
            content="Story content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=date(1453, 1, 1),
            date_end=date(1453, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            is_anonymous=False,
            created_at=datetime.now(timezone.utc),
            media_files=[],
            story_likes=[],
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(one_or_none=lambda: (mock_story, "authoruser")),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        with patch(
            "app.services.story_service.check_and_award_story_badges",
            new_callable=AsyncMock,
            return_value="First Story",
        ):
            result = await create_story_with_location(db, current_user, payload)

        assert result.title == "New Story"
        assert result.author == "authoruser"
        assert result.place_name == "Istanbul"
        assert result.latitude == 41.0082
        assert result.longitude == 28.9784
        assert result.date_start == date(1453, 1, 1)
        assert result.date_end == date(1453, 12, 31)
        assert result.date_precision == DatePrecision.YEAR
        assert result.status == StoryStatus.PUBLISHED
        assert result.visibility == StoryVisibility.PUBLIC
        assert result.media_files == []
        assert result.like_count == 0
        assert result.new_badge == "First Story"
        assert db.add.call_count == 2  # Story + auto-created StoryLocation
        assert db.commit.await_count == 2
        db.refresh.assert_not_awaited()

    async def test_create_story_with_empty_locations_list_adds_no_story_locations(self):
        payload = StoryCreateRequest(
            title="New Story",
            content="Story content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            locations=[],
        )
        current_user = SimpleNamespace(id=uuid.uuid4(), username="authoruser")

        mock_story = SimpleNamespace(
            id=uuid.uuid4(),
            title="New Story",
            content="Story content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=None,
            date_end=None,
            date_precision=None,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            is_anonymous=False,
            created_at=datetime.now(timezone.utc),
            media_files=[],
            story_likes=[],
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(one_or_none=lambda: (mock_story, "authoruser")),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        with patch("app.services.story_service.check_and_award_story_badges", new_callable=AsyncMock):
            result = await create_story_with_location(db, current_user, payload)

        # Only the Story is added; no auto-created StoryLocation for an explicit empty list
        assert result.title == "New Story"
        assert db.add.call_count == 1
        assert db.commit.await_count == 2
        db.refresh.assert_not_awaited()

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


@pytest.mark.asyncio
class TestUpdateStoryWithLocationAndDatesService:
    async def test_update_story_success(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id, user_id=uuid.uuid4())

        payload = StoryUpdateRequest(
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="Ankara",
            latitude=39.9334,
            longitude=32.8597,
            date_start=1920,
            date_end=1923,
        )
        current_user = SimpleNamespace(id=story.user_id, username="authoruser")

        mock_story_updated = SimpleNamespace(
            id=story_id,
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="Ankara",
            latitude=39.9334,
            longitude=32.8597,
            date_start=date(1920, 1, 1),
            date_end=date(1923, 12, 31),
            date_precision=DatePrecision.YEAR,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            is_anonymous=False,
            created_at=story.created_at,
            media_files=[],
            story_likes=[],
        )

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(one_or_none=lambda: (mock_story_updated, "authoruser")),
            SimpleNamespace(scalar_one=lambda: 4),
        ]

        result = await update_story_with_location_and_dates(db, story_id, current_user, payload)

        assert result.id == story_id
        assert result.title == "Updated Story"
        assert result.content == "Updated content"
        assert result.summary == "Updated summary"
        assert result.place_name == "Ankara"
        assert result.latitude == 39.9334
        assert result.longitude == 32.8597
        assert result.date_start == date(1920, 1, 1)
        assert result.date_end == date(1923, 12, 31)
        assert result.date_precision == DatePrecision.YEAR
        assert result.date_label == "1920 - 1923"
        assert result.like_count == 4
        assert result.media_files == []
        db.commit.assert_awaited_once()
        db.refresh.assert_not_awaited()

    async def test_update_story_not_found(self):
        payload = StoryUpdateRequest(
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="Ankara",
            latitude=39.9334,
            longitude=32.8597,
            date_start=1920,
            date_end=1923,
        )
        current_user = SimpleNamespace(id=uuid.uuid4(), username="authoruser")

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: None

        with pytest.raises(HTTPException) as exc_info:
            await update_story_with_location_and_dates(db, uuid.uuid4(), current_user, payload)

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"
        db.commit.assert_not_awaited()

    async def test_update_story_rejects_blank_place_name(self):
        story = _make_story(id=uuid.uuid4(), user_id=uuid.uuid4())
        payload = StoryUpdateRequest(
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="   ",
            latitude=39.9334,
            longitude=32.8597,
            date_start=1920,
            date_end=1923,
        )
        current_user = SimpleNamespace(id=story.user_id, username="authoruser")

        db = AsyncMock()
        db.execute.return_value.scalar_one_or_none = lambda: story

        with pytest.raises(HTTPException) as exc_info:
            await update_story_with_location_and_dates(db, story.id, current_user, payload)

        assert exc_info.value.status_code == 422
        assert "place_name is required" in exc_info.value.detail
        db.commit.assert_not_awaited()


@pytest.mark.asyncio
class TestGetNearbyStoriesService:
    async def test_returns_nearby_stories_and_total(self):
        story = _make_story()

        db = AsyncMock()
        db.execute.return_value.all = lambda: [(story, "storyauthor")]

        result = await get_nearby_stories(db, center_lat=41.0082, center_lng=28.9784)

        assert result.total == 1
        assert len(result.stories) == 1
        item = result.stories[0]
        assert item.id == story.id
        assert item.title == "Story Title"
        assert item.author == "storyauthor"
        assert item.latitude == 41.0082
        assert item.longitude == 28.9784
        db.execute.assert_awaited_once()

    async def test_returns_empty_response_when_no_stories_in_radius(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        result = await get_nearby_stories(db, center_lat=0.0, center_lng=0.0, radius_km=1.0)

        assert result.total == 0
        assert result.stories == []
        db.execute.assert_awaited_once()

    async def test_query_uses_haversine_formula(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_nearby_stories(db, center_lat=41.0082, center_lng=28.9784)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "asin" in sql
        assert "sqrt" in sql
        assert "sin" in sql
        assert "cos" in sql
        assert "radians" in sql

    async def test_query_filters_null_coordinates(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_nearby_stories(db, center_lat=41.0082, center_lng=28.9784)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "stories.latitude IS NOT NULL" in sql
        assert "stories.longitude IS NOT NULL" in sql

    async def test_query_filters_published_public_stories_only(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_nearby_stories(db, center_lat=41.0082, center_lng=28.9784)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "stories.status" in sql
        assert "stories.visibility" in sql

    async def test_query_orders_by_distance_ascending(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_nearby_stories(db, center_lat=41.0082, center_lng=28.9784)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "ORDER BY" in sql
        assert "DESC" not in sql


@pytest.mark.asyncio
class TestGetTimelineStoriesService:
    async def test_returns_stories_with_coord_filter(self):
        story = _make_story()
        db = AsyncMock()
        db.execute.return_value.all = lambda: [(story, "timelineauthor")]

        result = await get_timeline_stories(db, center_lat=41.0082, center_lng=28.9784, radius_km=5.0)

        assert result.total == 1
        assert result.stories[0].id == story.id
        db.execute.assert_awaited_once()

    async def test_returns_stories_with_place_name_filter(self):
        story = _make_story()
        db = AsyncMock()
        db.execute.return_value.all = lambda: [(story, "timelineauthor")]

        result = await get_timeline_stories(db, place_name="Istanbul")

        assert result.total == 1
        db.execute.assert_awaited_once()

    async def test_returns_empty_response_when_no_matches(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        result = await get_timeline_stories(db, place_name="Nowhere")

        assert result.total == 0
        assert result.stories == []

    async def test_query_orders_by_date_start_asc_nulls_last(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_timeline_stories(db, place_name="Istanbul")

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "ORDER BY" in sql
        assert "stories.date_start" in sql
        assert "NULLS LAST" in sql

    async def test_coord_filter_uses_haversine(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_timeline_stories(db, center_lat=41.0, center_lng=29.0, radius_km=5.0)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "asin" in sql
        assert "sqrt" in sql

    async def test_place_name_filter_uses_ilike(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_timeline_stories(db, place_name="kadikoy")

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "LIKE" in sql.upper()

    async def test_limit_and_offset_applied(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_timeline_stories(db, place_name="Istanbul", limit=5, offset=10)

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        assert "LIMIT" in sql.upper()
        assert "OFFSET" in sql.upper()

    async def test_coord_lookup_takes_priority_when_both_provided(self):
        db = AsyncMock()
        db.execute.return_value.all = lambda: []

        await get_timeline_stories(db, center_lat=41.0, center_lng=29.0, radius_km=5.0, place_name="Istanbul")

        stmt = db.execute.await_args.args[0]
        sql = str(stmt)

        # Haversine present (coord path), ILIKE absent (place_name ignored)
        assert "asin" in sql
        assert "LIKE" not in sql.upper()


class TestTagNormalizationHelpers:
    def test_normalize_tag_name_trims_and_lowercases(self):
        assert normalize_tag_name("  Ottoman  ") == "ottoman"

    def test_normalize_tag_name_rejects_blank_value(self):
        with pytest.raises(HTTPException) as exc_info:
            normalize_tag_name("   ")

        assert exc_info.value.status_code == 422
        assert exc_info.value.detail == "Tags cannot be blank"

    def test_normalize_tag_list_deduplicates_after_normalization(self):
        assert normalize_tag_list(["  History ", "history", "OTTOMAN "]) == ["history", "ottoman"]

    def test_normalize_tag_list_returns_empty_for_none(self):
        assert normalize_tag_list(None) == []

    def test_build_tag_slug_replaces_spaces_and_symbols(self):
        assert build_tag_slug("  Bogazici Universitesi!  ") == "bogazici-universitesi"

    def test_normalize_tag_name_rejects_values_longer_than_max_length(self):
        with pytest.raises(HTTPException) as exc_info:
            normalize_tag_name("a" * 101)

        assert exc_info.value.status_code == 422
        assert "at most 100 characters" in exc_info.value.detail


@pytest.mark.asyncio
class TestAiTagPersistenceHelpers:
    async def test_get_or_create_tags_returns_empty_without_hitting_db_for_empty_input(self):
        db = AsyncMock()

        tags = await get_or_create_tags(db, None)

        assert tags == []
        db.execute.assert_not_awaited()

    async def test_get_or_create_tags_reuses_existing_and_creates_missing(self):
        existing_tag = Tag(name="bogazici", slug="bogazici")
        new_tag = Tag(name="turkiye", slug="turkiye")
        new_tag.id = uuid.uuid4()
        db = AsyncMock()
        db.flush = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [existing_tag])),  # SELECT existing
            None,  # pg_insert ON CONFLICT DO NOTHING (result ignored)
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [existing_tag, new_tag])),  # SELECT all
        ]

        tags = await get_or_create_tags(db, [" Bogazici ", "Turkiye"])

        assert [tag.name for tag in tags] == ["bogazici", "turkiye"]
        assert tags[0] is existing_tag
        assert tags[1] is new_tag
        db.flush.assert_awaited_once()

    async def test_attach_tags_to_story_adds_only_missing_relations(self):
        existing_tag = Tag(name="bogazici", slug="bogazici")
        existing_tag.id = uuid.uuid4()
        new_tag = Tag(name="turkiye", slug="turkiye")
        new_tag.id = uuid.uuid4()
        story = _make_story(tags=[existing_tag])

        attach_tags_to_story(story, [existing_tag, new_tag])

        assert [tag.name for tag in story.tags] == ["bogazici", "turkiye"]

    async def test_attach_tags_to_story_keeps_existing_tag_only_once(self):
        existing_tag = Tag(name="bogazici", slug="bogazici")
        existing_tag.id = uuid.uuid4()
        story = _make_story(tags=[existing_tag])

        attach_tags_to_story(story, [existing_tag])

        assert [tag.name for tag in story.tags] == ["bogazici"]

    async def test_apply_ai_tags_to_story_attaches_tags_and_commits(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id, tags=[])
        existing_tag = Tag(name="bogazici", slug="bogazici")
        existing_tag.id = uuid.uuid4()
        new_tag = Tag(name="turkiye", slug="turkiye")
        new_tag.id = uuid.uuid4()

        db = AsyncMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),  # SELECT story
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [existing_tag])),  # SELECT existing tags
            None,  # pg_insert ON CONFLICT DO NOTHING
            SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [existing_tag, new_tag])),  # SELECT all
        ]

        updated_story = await apply_ai_tags_to_story(db, story_id, ["Bogazici", "Turkiye"])

        assert updated_story is story
        assert [tag.name for tag in story.tags] == ["bogazici", "turkiye"]
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(story, attribute_names=["tags"])

    async def test_apply_ai_tags_to_story_raises_404_when_story_missing(self):
        db = AsyncMock()
        db.execute.return_value = SimpleNamespace(scalar_one_or_none=lambda: None)

        with pytest.raises(HTTPException) as exc_info:
            await apply_ai_tags_to_story(db, uuid.uuid4(), ["bogazici"])

        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Story not found"
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


@pytest.mark.asyncio
class TestAnonymousStoryService:
    async def test_from_orm_with_author_masks_author_when_anonymous(self):
        story = _make_story(is_anonymous=True)

        response = StoryResponse.from_orm_with_author(story, "realauthor")

        assert response.author is None
        assert response.is_anonymous is True

    async def test_from_orm_with_author_exposes_author_when_not_anonymous(self):
        story = _make_story(is_anonymous=False)

        response = StoryResponse.from_orm_with_author(story, "realauthor")

        assert response.author == "realauthor"
        assert response.is_anonymous is False

    async def test_create_story_persists_is_anonymous_and_masks_author(self):
        payload = StoryCreateRequest(
            title="Anonymous Story",
            content="Content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            is_anonymous=True,
        )
        current_user = SimpleNamespace(id=uuid.uuid4(), username="realauthor")

        mock_story = SimpleNamespace(
            id=uuid.uuid4(),
            title="Anonymous Story",
            content="Content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=None,
            date_end=None,
            date_precision=None,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            is_anonymous=True,
            created_at=datetime.now(timezone.utc),
            media_files=[],
            story_likes=[],
        )

        db = AsyncMock()
        db.add = MagicMock()
        db.execute.side_effect = [
            SimpleNamespace(one_or_none=lambda: (mock_story, "realauthor")),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        with patch(
            "app.services.story_service.check_and_award_story_badges",
            new_callable=AsyncMock,
            return_value=None,
        ):
            result = await create_story_with_location(db, current_user, payload)

        assert result.is_anonymous is True
        assert result.author is None
        assert db.add.call_count == 2
        added_story = db.add.call_args_list[0].args[0]
        assert added_story.is_anonymous is True
        db.refresh.assert_not_awaited()

    async def test_update_story_sets_is_anonymous_and_masks_author(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id, user_id=uuid.uuid4(), is_anonymous=False)
        current_user = SimpleNamespace(id=story.user_id, username="realauthor")

        payload = StoryUpdateRequest(
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            is_anonymous=True,
        )

        mock_story_updated = SimpleNamespace(
            id=story_id,
            title="Updated Story",
            content="Updated content",
            summary="Summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=None,
            date_end=None,
            date_precision=None,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            is_anonymous=True,
            created_at=story.created_at,
            media_files=[],
            story_likes=[],
        )

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(one_or_none=lambda: (mock_story_updated, "realauthor")),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        result = await update_story_with_location_and_dates(db, story_id, current_user, payload)

        assert result.is_anonymous is True
        assert result.author is None
        assert story.is_anonymous is True
        db.commit.assert_awaited_once()

    async def test_update_story_omitting_is_anonymous_preserves_existing_value(self):
        story_id = uuid.uuid4()
        story = _make_story(id=story_id, user_id=uuid.uuid4(), is_anonymous=True)
        current_user = SimpleNamespace(id=story.user_id, username="realauthor")

        payload = StoryUpdateRequest(
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            # is_anonymous intentionally omitted
        )

        mock_story_updated = SimpleNamespace(
            id=story_id,
            title="Updated Story",
            content="Updated content",
            summary="Updated summary",
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=None,
            date_end=None,
            date_precision=None,
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            is_anonymous=True,
            created_at=story.created_at,
            media_files=[],
            story_likes=[],
        )

        db = AsyncMock()
        db.execute.side_effect = [
            SimpleNamespace(scalar_one_or_none=lambda: story),
            SimpleNamespace(one_or_none=lambda: (mock_story_updated, "realauthor")),
            SimpleNamespace(scalar_one=lambda: 0),
        ]

        result = await update_story_with_location_and_dates(db, story_id, current_user, payload)

        assert story.is_anonymous is True
        assert result.author is None
        db.commit.assert_awaited_once()
