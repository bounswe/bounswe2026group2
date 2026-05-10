import uuid
from datetime import date, datetime, timezone

import pytest
from sqlalchemy import func, select

from app.db.enums import DatePrecision, MediaType, StoryStatus, StoryVisibility
from app.db.media_file import MediaFile
from app.db.story import Story
from app.db.story_comment import StoryComment
from app.db.story_like import StoryLike
from app.db.story_save import StorySave
from app.db.user import User
from app.services.auth_service import hash_password


@pytest.mark.asyncio
class TestStoryListingAPI:
    async def test_list_stories_success(self, client, db_session):
        user = User(
            username="storyauthor",
            email="storyauthor@example.com",
            password_hash=hash_password("StoryPass1!"),
        )
        db_session.add(user)
        await db_session.flush()

        published_public_story = Story(
            user_id=user.id,
            title="Published Story",
            summary="A short summary",
            content="Story content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=date(1453, 1, 1),
            date_end=date(1453, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        hidden_story = Story(
            user_id=user.id,
            title="Draft Story",
            summary="Should not be listed",
            content="Draft content",
            status=StoryStatus.DRAFT,
            visibility=StoryVisibility.PRIVATE,
        )
        db_session.add_all([published_public_story, hidden_story])
        await db_session.commit()

        resp = await client.get("/stories")

        assert resp.status_code == 200
        data = resp.json()

        assert data["total"] == 1
        assert len(data["stories"]) == 1

        item = data["stories"][0]
        assert item["title"] == "Published Story"
        assert item["summary"] == "A short summary"
        assert item["content"] == "Story content"
        assert item["author"] == "storyauthor"
        assert item["place_name"] == "Istanbul"
        assert item["latitude"] == 41.0082
        assert item["longitude"] == 28.9784
        assert item["date_start"] == "1453-01-01"
        assert item["date_end"] == "1453-12-31"
        assert item["date_precision"] == "year"
        assert item["date_label"] == "1453"
        assert item["status"] == "published"
        assert item["visibility"] == "public"
        assert "id" in item
        assert "created_at" in item

    async def test_list_stories_empty(self, client):
        resp = await client.get("/stories")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"stories": [], "total": 0}

    async def test_list_stories_with_bounds_filters_results(self, client, db_session):
        user = User(
            username="mapauthor",
            email="mapauthor@example.com",
            password_hash=hash_password("StoryPass1!"),
        )
        db_session.add(user)
        await db_session.flush()

        in_bounds_story = Story(
            user_id=user.id,
            title="In Bounds",
            summary="Visible in viewport",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Istanbul",
            latitude=41.00,
            longitude=29.00,
        )
        out_bounds_story = Story(
            user_id=user.id,
            title="Out Bounds",
            summary="Outside viewport",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Ankara",
            latitude=39.93,
            longitude=32.85,
        )
        null_coord_story = Story(
            user_id=user.id,
            title="Null Coord",
            summary="No location",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Unknown",
            latitude=None,
            longitude=None,
        )
        db_session.add_all([in_bounds_story, out_bounds_story, null_coord_story])
        await db_session.commit()

        resp = await client.get("/stories?min_lat=40.9&max_lat=41.1&min_lng=28.9&max_lng=29.1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["stories"]) == 1
        assert data["stories"][0]["title"] == "In Bounds"

    async def test_list_stories_with_date_overlap_filters_results(self, client, db_session):
        user = User(
            username="timeauthor",
            email="timeauthor@example.com",
            password_hash=hash_password("StoryPass1!"),
        )
        db_session.add(user)
        await db_session.flush()

        in_range_story = Story(
            user_id=user.id,
            title="Year 2025 Story",
            summary="story in 2025",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Istanbul",
            latitude=41.00,
            longitude=29.00,
            date_start=date(2025, 1, 1),
            date_end=date(2025, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        out_range_story = Story(
            user_id=user.id,
            title="Year 1800 Story",
            summary="story in 1800",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Ankara",
            latitude=39.93,
            longitude=32.85,
            date_start=date(1800, 1, 1),
            date_end=date(1800, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        db_session.add_all([in_range_story, out_range_story])
        await db_session.commit()

        resp = await client.get("/stories?query_start=2025-08-01&query_end=2025-08-31&query_precision=date")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Year 2025 Story"

    async def test_list_stories_with_incomplete_bounds_returns_422(self, client):
        resp = await client.get("/stories?min_lat=40.9&max_lat=41.1")

        assert resp.status_code == 422

    async def test_list_stories_with_invalid_bounds_order_returns_422(self, client):
        resp = await client.get("/stories?min_lat=41.1&max_lat=40.9&min_lng=28.9&max_lng=29.1")

        assert resp.status_code == 422


@pytest.mark.asyncio
class TestStoryMediaUploadAPI:
    async def _create_user_and_token(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "mediauser",
                "email": "media@example.com",
                "password": "MediaPass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "media@example.com",
                "password": "MediaPass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_upload_media_success(self, client, db_session, monkeypatch):
        token = await self._create_user_and_token(client)

        user = User(
            username="storyowner",
            email="storyowner@example.com",
            password_hash=hash_password("StoryOwner1!"),
        )
        db_session.add(user)
        await db_session.flush()

        story = Story(
            user_id=user.id,
            title="Story with media",
            summary="summary",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        )
        db_session.add(story)
        await db_session.commit()

        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)

        resp = await client.post(
            f"/stories/{story.id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "media_type": "image",
                "alt_text": "alt",
                "caption": "caption",
                "sort_order": "1",
            },
            files={"file": ("photo.png", b"png-bytes", "image/png")},
        )

        assert resp.status_code == 201
        payload = resp.json()
        media = payload["media"]
        assert media["story_id"] == str(story.id)
        assert media["original_filename"] == "photo.png"
        assert media["mime_type"] == "image/png"
        assert media["media_type"] == "image"
        assert media["file_size_bytes"] == len(b"png-bytes")
        assert media["sort_order"] == 1
        assert media["alt_text"] == "alt"
        assert media["caption"] == "caption"
        assert "id" in media
        assert "storage_key" in media
        assert "bucket_name" in media
        assert media["media_url"].endswith(f"/{media['bucket_name']}/{media['storage_key']}")
        assert "created_at" in media

    async def test_upload_media_invalid_mime_type(self, client, db_session, monkeypatch):
        token = await self._create_user_and_token(client)

        user = User(
            username="storyowner2",
            email="storyowner2@example.com",
            password_hash=hash_password("StoryOwner2!"),
        )
        db_session.add(user)
        await db_session.flush()

        story = Story(
            user_id=user.id,
            title="Story invalid media",
            summary="summary",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        )
        db_session.add(story)
        await db_session.commit()

        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)

        resp = await client.post(
            f"/stories/{story.id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "image"},
            files={"file": ("clip.mp4", b"video-bytes", "video/mp4")},
        )

        assert resp.status_code == 422
        assert "Unsupported mime type" in resp.json()["detail"]


@pytest.mark.asyncio
class TestStoryDetailAPI:
    async def test_get_story_detail_success(self, client, db_session):
        user = User(
            username="detailauthor",
            email="detailauthor@example.com",
            password_hash=hash_password("DetailPass1!"),
        )
        db_session.add(user)
        await db_session.flush()

        story = Story(
            user_id=user.id,
            title="Detail Story",
            summary="Detail summary",
            content="Detail content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Ankara",
            latitude=39.9334,
            longitude=32.8597,
            date_start=date(1923, 1, 1),
            date_end=date(1923, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        db_session.add(story)
        await db_session.flush()

        media = MediaFile(
            story_id=story.id,
            bucket_name="images",
            storage_key="stories/test/photo.png",
            original_filename="photo.png",
            mime_type="image/png",
            media_type=MediaType.IMAGE,
            file_size_bytes=777,
            sort_order=0,
            alt_text="test alt",
            caption="test caption",
        )
        db_session.add(media)
        await db_session.commit()

        resp = await client.get(f"/stories/{story.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(story.id)
        assert data["title"] == "Detail Story"
        assert data["summary"] == "Detail summary"
        assert data["content"] == "Detail content"
        assert data["author"] == "detailauthor"
        assert data["place_name"] == "Ankara"
        assert data["date_start"] == "1923-01-01"
        assert data["date_end"] == "1923-12-31"
        assert data["date_precision"] == "year"
        assert data["date_label"] == "1923"
        assert data["status"] == "published"
        assert data["visibility"] == "public"
        assert data["like_count"] == 0
        assert "created_at" in data

        assert len(data["media_files"]) == 1
        media_item = data["media_files"][0]
        assert media_item["story_id"] == str(story.id)
        assert media_item["original_filename"] == "photo.png"
        assert media_item["mime_type"] == "image/png"
        assert media_item["media_type"] == "image"
        assert media_item["file_size_bytes"] == 777
        assert media_item["media_url"].endswith("/images/stories/test/photo.png")
        assert media_item["transcript"] is None

    async def test_get_story_detail_includes_audio_transcript_when_present(self, client, db_session):
        author = User(
            username="detailaudioauthor",
            email="detailaudioauthor@example.com",
            password_hash="hashed-password",
        )
        db_session.add(author)
        await db_session.flush()

        story = Story(
            user_id=author.id,
            title="Audio Detail Story",
            summary="Audio summary",
            content="Audio content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=date(1923, 1, 1),
            date_end=date(1923, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        db_session.add(story)
        await db_session.flush()

        media = MediaFile(
            story_id=story.id,
            bucket_name="audio",
            storage_key="stories/test/audio.webm",
            original_filename="audio.webm",
            mime_type="audio/webm",
            media_type=MediaType.AUDIO,
            file_size_bytes=321,
            sort_order=0,
            transcript="Transcribed local history narration",
        )
        db_session.add(media)
        await db_session.commit()

        resp = await client.get(f"/stories/{story.id}")

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["media_files"]) == 1
        assert data["media_files"][0]["transcript"] == "Transcribed local history narration"

    async def test_get_story_detail_not_found(self, client):
        resp = await client.get(f"/stories/{uuid.uuid4()}")

        assert resp.status_code == 404
        data = resp.json()
        assert data["detail"] == "Story not found"


@pytest.mark.asyncio
class TestStoryLikeAPI:
    async def _create_user_and_token(self, client, username, email):
        await client.post(
            "/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "StoryLike1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "StoryLike1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_like_story_success(self, client):
        author_token = await self._create_user_and_token(client, "likeauthorapi", "likeauthorapi@example.com")
        liker_token = await self._create_user_and_token(client, "likerapi", "likerapi@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "API Like Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )
        story_id = create_resp.json()["id"]

        resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "story_id": story_id,
            "liked": True,
            "like_count": 1,
        }

    async def test_get_like_summary_returns_unliked_state(self, client):
        author_token = await self._create_user_and_token(client, "likeauthorapi6", "likeauthorapi6@example.com")
        liker_token = await self._create_user_and_token(client, "likerapi6", "likerapi6@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "API Like Summary Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Bursa",
                "latitude": 40.195,
                "longitude": 29.06,
            },
        )
        story_id = create_resp.json()["id"]

        resp = await client.get(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "story_id": story_id,
            "liked": False,
            "like_count": 0,
        }

    async def test_get_like_summary_returns_liked_state(self, client):
        author_token = await self._create_user_and_token(client, "likeauthorapi7", "likeauthorapi7@example.com")
        liker_token = await self._create_user_and_token(client, "likerapi7", "likerapi7@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "API Like Summary Liked Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Eskisehir",
                "latitude": 39.7667,
                "longitude": 30.5256,
            },
        )
        story_id = create_resp.json()["id"]

        await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        resp = await client.get(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == {
            "story_id": story_id,
            "liked": True,
            "like_count": 1,
        }

    async def test_duplicate_like_is_idempotent_and_persists_once(self, client, db_session):
        author_token = await self._create_user_and_token(client, "likeauthorapi2", "likeauthorapi2@example.com")
        liker_token = await self._create_user_and_token(client, "likerapi2", "likerapi2@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Duplicate Like Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
            },
        )
        story_id = create_resp.json()["id"]

        first_resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )
        second_resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        like_count_result = await db_session.execute(
            select(func.count(StoryLike.id)).where(StoryLike.story_id == uuid.UUID(story_id))
        )

        assert first_resp.status_code == 200
        assert second_resp.status_code == 200
        assert first_resp.json()["like_count"] == 1
        assert second_resp.json()["like_count"] == 1
        assert like_count_result.scalar_one() == 1

    async def test_unlike_story_success_and_repeat_is_idempotent(self, client):
        author_token = await self._create_user_and_token(client, "likeauthorapi3", "likeauthorapi3@example.com")
        liker_token = await self._create_user_and_token(client, "likerapi3", "likerapi3@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Unlike Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Izmir",
                "latitude": 38.4237,
                "longitude": 27.1428,
            },
        )
        story_id = create_resp.json()["id"]

        await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        first_unlike = await client.delete(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )
        second_unlike = await client.delete(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )
        detail_resp = await client.get(f"/stories/{story_id}")

        assert first_unlike.status_code == 200
        assert second_unlike.status_code == 200
        assert first_unlike.json()["liked"] is False
        assert second_unlike.json()["liked"] is False
        assert first_unlike.json()["like_count"] == 0
        assert second_unlike.json()["like_count"] == 0
        assert detail_resp.json()["like_count"] == 0

    async def test_like_story_missing_story_returns_404(self, client):
        liker_token = await self._create_user_and_token(client, "likerapi4", "likerapi4@example.com")

        resp = await client.post(
            f"/stories/{uuid.uuid4()}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"

    async def test_unlike_story_missing_story_returns_404(self, client):
        liker_token = await self._create_user_and_token(client, "likerapi5", "likerapi5@example.com")

        resp = await client.delete(
            f"/stories/{uuid.uuid4()}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"

    async def test_get_like_summary_missing_story_returns_404(self, client):
        liker_token = await self._create_user_and_token(client, "likerapi8", "likerapi8@example.com")

        resp = await client.get(
            f"/stories/{uuid.uuid4()}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"

    async def test_like_story_requires_authentication(self, client):
        resp = await client.post(f"/stories/{uuid.uuid4()}/like")

        assert resp.status_code == 401

    async def test_get_like_summary_requires_authentication(self, client):
        resp = await client.get(f"/stories/{uuid.uuid4()}/like")

        assert resp.status_code == 401


@pytest.mark.asyncio
class TestStoryCreateAPI:
    async def _create_user_and_token(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "createuser",
                "email": "create@example.com",
                "password": "CreatePass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "create@example.com",
                "password": "CreatePass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_create_story_with_location_success(self, client):
        token = await self._create_user_and_token(client)

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Created Story",
                "content": "Created content",
                "summary": "Created summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
                "date_end": 1453,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Created Story"
        assert data["content"] == "Created content"
        assert data["summary"] == "Created summary"
        assert data["author"] == "createuser"
        assert data["place_name"] == "Istanbul"
        assert data["latitude"] == 41.0082
        assert data["longitude"] == 28.9784
        assert data["date_start"] == "1453-01-01"
        assert data["date_end"] == "1453-12-31"
        assert data["date_precision"] == "year"
        assert data["date_label"] == "1453"
        assert data["status"] == "published"
        assert data["visibility"] == "public"
        assert data["media_files"] == []
        assert "id" in data
        assert "created_at" in data

    async def test_create_story_with_blank_place_name_returns_422(self, client):
        token = await self._create_user_and_token(client)

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Created Story",
                "content": "Created content",
                "place_name": "   ",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 422
        assert "place_name is required" in resp.json()["detail"]

    async def test_create_story_with_single_start_date_returns_single_date_label(self, client):
        token = await self._create_user_and_token(client)

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Created Story",
                "content": "Created content",
                "summary": "Created summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["date_start"] == "1453-01-01"
        assert data["date_end"] == "1453-12-31"
        assert data["date_precision"] == "year"
        assert data["date_label"] == "1453"


@pytest.mark.asyncio
class TestStoryUpdateAPI:
    async def _create_user_and_token(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "updateuser",
                "email": "update@example.com",
                "password": "UpdatePass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "update@example.com",
                "password": "UpdatePass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_update_story_success(self, client):
        token = await self._create_user_and_token(client)

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Original Story",
                "content": "Original content",
                "summary": "Original summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1400,
                "date_end": 1453,
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/stories/{story_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Updated Story",
                "content": "Updated content",
                "summary": "Updated summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "date_start": 1920,
                "date_end": 1923,
            },
        )

        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["id"] == story_id
        assert data["title"] == "Updated Story"
        assert data["content"] == "Updated content"
        assert data["summary"] == "Updated summary"
        assert data["place_name"] == "Ankara"
        assert data["latitude"] == 39.9334
        assert data["longitude"] == 32.8597
        assert data["date_start"] == "1920-01-01"
        assert data["date_end"] == "1923-12-31"
        assert data["date_precision"] == "year"
        assert data["date_label"] == "1920 - 1923"

    async def test_update_story_invalid_date_range_returns_422(self, client):
        token = await self._create_user_and_token(client)

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Original Story",
                "content": "Original content",
                "summary": "Original summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1400,
                "date_end": 1453,
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/stories/{story_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Updated Story",
                "content": "Updated content",
                "summary": "Updated summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "date_start": 1923,
                "date_end": 1920,
            },
        )

        assert update_resp.status_code == 422
        assert "date_end must be greater than or equal to date_start" in str(update_resp.json())

    async def test_update_story_not_found_returns_404(self, client):
        token = await self._create_user_and_token(client)

        update_resp = await client.put(
            f"/stories/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Updated Story",
                "content": "Updated content",
                "summary": "Updated summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "date_start": 1920,
                "date_end": 1923,
            },
        )

        assert update_resp.status_code == 404
        assert update_resp.json()["detail"] == "Story not found"


# --- Issue #133: Story Creation Endpoint (additional cases) ---


@pytest.mark.asyncio
class TestStoryCreateAuthAPI:
    """Additional creation tests covering #133 — auth rejection and validation."""

    async def test_create_story_unauthenticated_returns_401(self, client):
        resp = await client.post(
            "/stories",
            json={
                "title": "No Auth Story",
                "content": "Some content",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 401

    async def test_create_story_missing_title_returns_422(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "notitleuser",
                "email": "notitle@example.com",
                "password": "NoTitle1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "notitle@example.com", "password": "NoTitle1!"},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "content": "No title content",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 422

    async def test_create_story_missing_content_returns_422(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "nocontentuser",
                "email": "nocontent@example.com",
                "password": "NoContent1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "nocontent@example.com", "password": "NoContent1!"},
        )
        token = login_resp.json()["access_token"]

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "No Content Story",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 422


# --- Issue #134: Story Retrieval Endpoint (additional cases) ---


@pytest.mark.asyncio
class TestStoryRetrievalAPI:
    """Additional retrieval tests covering #134 — invalid ID format."""

    async def test_get_story_with_invalid_uuid_returns_422(self, client):
        resp = await client.get("/stories/not-a-uuid")

        assert resp.status_code == 422


@pytest.mark.asyncio
class TestStoryCommentAPI:
    async def _create_user_and_token(self, client, username, email):
        await client.post(
            "/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "CommentPass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "CommentPass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_create_comment_success(self, client):
        author_token = await self._create_user_and_token(client, "commentauthor", "commentauthor@example.com")
        commenter_token = await self._create_user_and_token(client, "commenter", "commenter@example.com")

        create_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Story With Comments",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )
        story_id = create_story_resp.json()["id"]

        resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "Great story"},
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["story_id"] == story_id
        assert data["content"] == "Great story"
        assert data["author"]["username"] == "commenter"
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_comment_requires_authentication(self, client):
        resp = await client.post(f"/stories/{uuid.uuid4()}/comments", json={"content": "Hello"})
        assert resp.status_code == 401

    async def test_create_comment_rejects_blank_content(self, client):
        author_token = await self._create_user_and_token(client, "commentauthor2", "commentauthor2@example.com")
        commenter_token = await self._create_user_and_token(client, "commenter2", "commenter2@example.com")

        create_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Story With Blank Comment",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
            },
        )
        story_id = create_story_resp.json()["id"]

        resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "   "},
        )

        assert resp.status_code == 422
        detail = resp.json()["detail"]
        assert isinstance(detail, list)
        assert detail[0]["loc"] == ["body", "content"]

    async def test_create_comment_missing_story_returns_404(self, client):
        commenter_token = await self._create_user_and_token(client, "commenter3", "commenter3@example.com")

        resp = await client.post(
            f"/stories/{uuid.uuid4()}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "Hello"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"

    async def test_list_comments_success_in_chronological_order(self, client, db_session):
        story_author = User(
            username="storycommentauthor",
            email="storycommentauthor@example.com",
            password_hash=hash_password("StoryPass1!"),
            display_name="Story Author",
        )
        first_commenter = User(
            username="firstcommenter",
            email="firstcommenter@example.com",
            password_hash=hash_password("StoryPass1!"),
            display_name="First Commenter",
        )
        second_commenter = User(
            username="secondcommenter",
            email="secondcommenter@example.com",
            password_hash=hash_password("StoryPass1!"),
            display_name="Second Commenter",
        )
        db_session.add_all([story_author, first_commenter, second_commenter])
        await db_session.flush()

        story = Story(
            user_id=story_author.id,
            title="Comment List Story",
            summary="summary",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
        )
        db_session.add(story)
        await db_session.flush()

        first_comment = StoryComment(
            story_id=story.id,
            user_id=first_commenter.id,
            content="First comment",
            created_at=datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 19, 12, 0, tzinfo=timezone.utc),
        )
        second_comment = StoryComment(
            story_id=story.id,
            user_id=second_commenter.id,
            content="Second comment",
            created_at=datetime(2026, 4, 19, 12, 5, tzinfo=timezone.utc),
            updated_at=datetime(2026, 4, 19, 12, 5, tzinfo=timezone.utc),
        )
        db_session.add_all([first_comment, second_comment])
        await db_session.commit()

        resp = await client.get(f"/stories/{story.id}/comments")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert [comment["content"] for comment in data["comments"]] == ["First comment", "Second comment"]
        assert data["comments"][0]["author"]["username"] == "firstcommenter"
        assert data["comments"][1]["author"]["display_name"] == "Second Commenter"

    async def test_list_comments_missing_story_returns_404(self, client):
        resp = await client.get(f"/stories/{uuid.uuid4()}/comments")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"

    async def test_delete_comment_success_for_owner(self, client):
        author_token = await self._create_user_and_token(client, "commentauthor4", "commentauthor4@example.com")
        commenter_token = await self._create_user_and_token(client, "commenter4", "commenter4@example.com")

        create_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Story With Deletable Comment",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Izmir",
                "latitude": 38.4237,
                "longitude": 27.1428,
            },
        )
        story_id = create_story_resp.json()["id"]

        create_comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "Delete me"},
        )
        comment_id = create_comment_resp.json()["id"]

        delete_resp = await client.delete(
            f"/stories/{story_id}/comments/{comment_id}",
            headers={"Authorization": f"Bearer {commenter_token}"},
        )
        list_resp = await client.get(f"/stories/{story_id}/comments")

        assert delete_resp.status_code == 204
        assert list_resp.status_code == 200
        assert list_resp.json() == {"comments": [], "total": 0}

    async def test_delete_comment_returns_403_for_non_owner(self, client):
        author_token = await self._create_user_and_token(client, "commentauthor5", "commentauthor5@example.com")
        owner_token = await self._create_user_and_token(client, "commentowner5", "commentowner5@example.com")
        other_user_token = await self._create_user_and_token(client, "commentother5", "commentother5@example.com")

        create_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Story With Protected Comment",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Bursa",
                "latitude": 40.1826,
                "longitude": 29.0665,
            },
        )
        story_id = create_story_resp.json()["id"]

        create_comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {owner_token}"},
            json={"content": "Cannot delete me"},
        )
        comment_id = create_comment_resp.json()["id"]

        delete_resp = await client.delete(
            f"/stories/{story_id}/comments/{comment_id}",
            headers={"Authorization": f"Bearer {other_user_token}"},
        )

        assert delete_resp.status_code == 403
        assert delete_resp.json()["detail"] == "Not allowed to delete this comment"

    async def test_delete_comment_missing_comment_returns_404(self, client):
        commenter_token = await self._create_user_and_token(client, "commenter6", "commenter6@example.com")
        author_token = await self._create_user_and_token(client, "commentauthor6", "commentauthor6@example.com")

        create_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Story For Missing Comment",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Adana",
                "latitude": 37.0,
                "longitude": 35.3213,
            },
        )
        story_id = create_story_resp.json()["id"]

        delete_resp = await client.delete(
            f"/stories/{story_id}/comments/{uuid.uuid4()}",
            headers={"Authorization": f"Bearer {commenter_token}"},
        )

        assert delete_resp.status_code == 404
        assert delete_resp.json()["detail"] == "Comment not found"


# --- Issue #135: Story Search Endpoint ---


@pytest.mark.asyncio
class TestStorySearchAPI:
    """API tests for GET /stories/search covering #135."""

    async def _seed_stories(self, db_session):
        from datetime import date

        from app.db.enums import DatePrecision, StoryStatus, StoryVisibility
        from app.db.story import Story
        from app.db.user import User
        from app.services.auth_service import hash_password

        user = User(
            username="searchauthor",
            email="searchauthor@example.com",
            password_hash=hash_password("SearchPass1!"),
        )
        db_session.add(user)
        await db_session.flush()

        istanbul_story = Story(
            user_id=user.id,
            title="Istanbul Story",
            summary="About Istanbul",
            content="Content about Istanbul",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            date_start=date(1453, 1, 1),
            date_end=date(1453, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        ankara_story = Story(
            user_id=user.id,
            title="Ankara Story",
            summary="About Ankara",
            content="Content about Ankara",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Ankara",
            latitude=39.9334,
            longitude=32.8597,
            date_start=date(1923, 1, 1),
            date_end=date(1923, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        draft_istanbul_story = Story(
            user_id=user.id,
            title="Draft Istanbul Story",
            summary="Draft about Istanbul",
            content="Draft content",
            status=StoryStatus.DRAFT,
            visibility=StoryVisibility.PRIVATE,
            place_name="Istanbul",
        )
        db_session.add_all([istanbul_story, ankara_story, draft_istanbul_story])
        await db_session.commit()

        return istanbul_story, ankara_story

    async def test_search_by_place_name_returns_matching_stories(self, client, db_session):
        await self._seed_stories(db_session)

        resp = await client.get("/stories/search?place_name=Istanbul")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Istanbul Story"
        assert data["stories"][0]["place_name"] == "Istanbul"

    async def test_search_by_place_name_returns_only_public_published(self, client, db_session):
        await self._seed_stories(db_session)

        resp = await client.get("/stories/search?place_name=Istanbul")

        assert resp.status_code == 200
        data = resp.json()
        titles = [s["title"] for s in data["stories"]]
        assert "Draft Istanbul Story" not in titles

    async def test_search_by_place_name_no_match_returns_empty(self, client, db_session):
        await self._seed_stories(db_session)

        resp = await client.get("/stories/search?place_name=Trabzon")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"stories": [], "total": 0}

    async def test_search_with_date_filter_narrows_results(self, client, db_session):
        from datetime import date

        from app.db.enums import DatePrecision, StoryStatus, StoryVisibility
        from app.db.story import Story
        from app.db.user import User
        from app.services.auth_service import hash_password

        user = User(
            username="datefilterauthor",
            email="datefilterauthor@example.com",
            password_hash=hash_password("DateFilter1!"),
        )
        db_session.add(user)
        await db_session.flush()

        old_story = Story(
            user_id=user.id,
            title="Old Izmir Story",
            summary="Old",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Izmir",
            latitude=38.4192,
            longitude=27.1287,
            date_start=date(1800, 1, 1),
            date_end=date(1800, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        recent_story = Story(
            user_id=user.id,
            title="Recent Izmir Story",
            summary="Recent",
            content="content",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Izmir",
            latitude=38.4192,
            longitude=27.1287,
            date_start=date(2020, 1, 1),
            date_end=date(2020, 12, 31),
            date_precision=DatePrecision.YEAR,
        )
        db_session.add_all([old_story, recent_story])
        await db_session.commit()

        resp = await client.get(
            "/stories/search?place_name=Izmir&query_start=2020-01-01&query_end=2020-12-31&query_precision=date"
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Recent Izmir Story"

    async def test_search_missing_place_name_returns_422(self, client):
        resp = await client.get("/stories/search")

        assert resp.status_code == 422

    async def test_search_empty_place_name_returns_422(self, client):
        resp = await client.get("/stories/search?place_name=")

        assert resp.status_code == 422


@pytest.mark.asyncio
class TestStorySaveAPI:
    async def _create_user_and_token(self, client, username, email):
        await client.post(
            "/auth/register",
            json={
                "username": username,
                "email": email,
                "password": "SavePass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": email,
                "password": "SavePass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_save_story_success(self, client):
        author_token = await self._create_user_and_token(client, "saveauthor", "saveauthor@example.com")
        saver_token = await self._create_user_and_token(client, "saveruser", "saver@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Savable Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )
        story_id = create_resp.json()["id"]

        resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        assert resp.status_code == 200
        assert resp.json() == {"story_id": story_id, "saved": True}

    async def test_duplicate_save_is_idempotent_and_persists_once(self, client, db_session):
        author_token = await self._create_user_and_token(client, "saveauthor2", "saveauthor2@example.com")
        saver_token = await self._create_user_and_token(client, "saveruser2", "saver2@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Duplicate Save Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
            },
        )
        story_id = create_resp.json()["id"]

        first_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )
        second_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        save_result = await db_session.execute(select(StorySave).where(StorySave.story_id == uuid.UUID(story_id)))
        saves = save_result.scalars().all()

        assert first_resp.status_code == 200
        assert second_resp.status_code == 200
        assert first_resp.json()["saved"] is True
        assert second_resp.json()["saved"] is True
        assert len(saves) == 1

    async def test_unsave_story_success_and_repeat_is_idempotent(self, client):
        author_token = await self._create_user_and_token(client, "saveauthor3", "saveauthor3@example.com")
        saver_token = await self._create_user_and_token(client, "saveruser3", "saver3@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Unsave Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Izmir",
                "latitude": 38.4237,
                "longitude": 27.1428,
            },
        )
        story_id = create_resp.json()["id"]

        await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        first_unsave = await client.delete(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )
        second_unsave = await client.delete(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        assert first_unsave.status_code == 200
        assert second_unsave.status_code == 200
        assert first_unsave.json() == {"story_id": story_id, "saved": False}
        assert second_unsave.json() == {"story_id": story_id, "saved": False}

    async def test_list_saved_stories_returns_only_current_users_saves(self, client):
        author_token = await self._create_user_and_token(client, "saveauthor4", "saveauthor4@example.com")
        saver_one_token = await self._create_user_and_token(client, "saveruser4", "saver4@example.com")
        saver_two_token = await self._create_user_and_token(client, "saveruser5", "saver5@example.com")

        first_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "First Saved Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )
        second_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Second Saved Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Bursa",
                "latitude": 40.1826,
                "longitude": 29.0665,
            },
        )
        first_story_id = first_story_resp.json()["id"]
        second_story_id = second_story_resp.json()["id"]

        await client.post(f"/stories/{first_story_id}/save", headers={"Authorization": f"Bearer {saver_one_token}"})
        await client.post(f"/stories/{second_story_id}/save", headers={"Authorization": f"Bearer {saver_two_token}"})

        resp = await client.get("/stories/saved", headers={"Authorization": f"Bearer {saver_one_token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "First Saved Story"

    async def test_list_saved_stories_excludes_saved_stories_that_are_no_longer_public(self, client, db_session):
        author_token = await self._create_user_and_token(client, "saveauthor5", "saveauthor5@example.com")
        saver_token = await self._create_user_and_token(client, "saveruser7", "saver7@example.com")

        public_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Still Public Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )
        hidden_story_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {author_token}"},
            json={
                "title": "Later Hidden Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
            },
        )
        public_story_id = public_story_resp.json()["id"]
        hidden_story_id = hidden_story_resp.json()["id"]

        await client.post(f"/stories/{public_story_id}/save", headers={"Authorization": f"Bearer {saver_token}"})
        await client.post(f"/stories/{hidden_story_id}/save", headers={"Authorization": f"Bearer {saver_token}"})

        hidden_story = await db_session.get(Story, uuid.UUID(hidden_story_id))
        hidden_story.visibility = StoryVisibility.PRIVATE
        await db_session.commit()

        resp = await client.get("/stories/saved", headers={"Authorization": f"Bearer {saver_token}"})

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert [story["id"] for story in data["stories"]] == [public_story_id]

    async def test_save_story_missing_story_returns_404(self, client):
        saver_token = await self._create_user_and_token(client, "saveruser6", "saver6@example.com")

        resp = await client.post(
            f"/stories/{uuid.uuid4()}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"

    async def test_saved_story_endpoints_require_authentication(self, client):
        save_resp = await client.post(f"/stories/{uuid.uuid4()}/save")
        list_resp = await client.get("/stories/saved")

        assert save_resp.status_code == 401
        assert list_resp.status_code == 401


@pytest.mark.asyncio
class TestNearbyStoriesAPI:
    def _make_user(self, username: str, email: str) -> User:
        return User(
            username=username,
            email=email,
            password_hash=hash_password("TestPass1!"),
        )

    def _make_story(self, user_id, title, lat, lng, place_name="Istanbul") -> Story:
        return Story(
            user_id=user_id,
            title=title,
            content="content",
            summary="summary",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name=place_name,
            latitude=lat,
            longitude=lng,
        )

    async def test_returns_story_within_radius(self, client, db_session):
        user = self._make_user("nearbyauthor1", "nearby1@example.com")
        db_session.add(user)
        await db_session.flush()

        # Çeliktepe, Istanbul — ~0.4 km from query centre
        story = self._make_story(user.id, "Nearby Story", lat=41.0739, lng=28.9606)
        db_session.add(story)
        await db_session.commit()

        resp = await client.get("/stories/nearby?lat=41.0770&lng=28.9620&radius_km=5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Nearby Story"

    async def test_excludes_story_outside_radius(self, client, db_session):
        user = self._make_user("nearbyauthor2", "nearby2@example.com")
        db_session.add(user)
        await db_session.flush()

        # Ankara — ~350 km from Istanbul
        story = self._make_story(user.id, "Far Away Story", lat=39.9334, lng=32.8597, place_name="Ankara")
        db_session.add(story)
        await db_session.commit()

        resp = await client.get("/stories/nearby?lat=41.0082&lng=28.9784&radius_km=10")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    async def test_returns_empty_when_no_stories_exist(self, client):
        resp = await client.get("/stories/nearby?lat=41.0082&lng=28.9784")

        assert resp.status_code == 200
        assert resp.json() == {"stories": [], "total": 0}

    async def test_invalid_lat_returns_422(self, client):
        resp = await client.get("/stories/nearby?lat=999&lng=28.9784")

        assert resp.status_code == 422

    async def test_invalid_lng_returns_422(self, client):
        resp = await client.get("/stories/nearby?lat=41.0082&lng=999")

        assert resp.status_code == 422

    async def test_non_positive_radius_returns_422(self, client):
        resp = await client.get("/stories/nearby?lat=41.0082&lng=28.9784&radius_km=0")

        assert resp.status_code == 422

    async def test_missing_lat_returns_422(self, client):
        resp = await client.get("/stories/nearby?lng=28.9784")

        assert resp.status_code == 422

    async def test_missing_lng_returns_422(self, client):
        resp = await client.get("/stories/nearby?lat=41.0082")

        assert resp.status_code == 422


@pytest.mark.asyncio
class TestAnonymousStoryAPI:
    async def _create_user_and_token(self, client, username: str, email: str) -> str:
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": "AnonPass1!"},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": "AnonPass1!"},
        )
        return login_resp.json()["access_token"]

    async def test_create_anonymous_story_returns_null_author(self, client):
        token = await self._create_user_and_token(client, "anonuser1", "anon1@example.com")

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Anonymous Story",
                "content": "Secret content",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "is_anonymous": True,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["author"] is None
        assert data["is_anonymous"] is True

    async def test_create_non_anonymous_story_returns_real_author(self, client):
        token = await self._create_user_and_token(client, "anonuser2", "anon2@example.com")

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Named Story",
                "content": "Public content",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "is_anonymous": False,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["author"] == "anonuser2"
        assert data["is_anonymous"] is False

    async def test_list_stories_hides_author_for_anonymous_story(self, client, db_session):
        user = User(
            username="anonlistuser",
            email="anonlist@example.com",
            password_hash=hash_password("AnonPass1!"),
        )
        db_session.add(user)
        await db_session.flush()

        story = Story(
            user_id=user.id,
            title="Anonymous Listed Story",
            content="content",
            summary="summary",
            status=StoryStatus.PUBLISHED,
            visibility=StoryVisibility.PUBLIC,
            place_name="Istanbul",
            latitude=41.0082,
            longitude=28.9784,
            is_anonymous=True,
        )
        db_session.add(story)
        await db_session.commit()

        resp = await client.get("/stories")

        assert resp.status_code == 200
        items = [s for s in resp.json()["stories"] if s["title"] == "Anonymous Listed Story"]
        assert len(items) == 1
        assert items[0]["author"] is None
        assert items[0]["is_anonymous"] is True

    async def test_update_story_to_anonymous_hides_author(self, client):
        token = await self._create_user_and_token(client, "anonuser3", "anon3@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Will Be Anonymous",
                "content": "content",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "is_anonymous": False,
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]
        assert create_resp.json()["author"] == "anonuser3"

        update_resp = await client.put(
            f"/stories/{story_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Will Be Anonymous",
                "content": "content",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "is_anonymous": True,
            },
        )

        assert update_resp.status_code == 200
        data = update_resp.json()
        assert data["author"] is None
        assert data["is_anonymous"] is True
