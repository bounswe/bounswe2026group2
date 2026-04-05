import pytest

from app.db.enums import StoryStatus, StoryVisibility
from app.db.story import Story
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
            date_start=1453,
            date_end=1453,
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
        assert item["date_start"] == 1453
        assert item["date_end"] == 1453
        assert item["date_label"] == "1453 - 1453"
        assert item["status"] == "published"
        assert item["visibility"] == "public"
        assert "id" in item
        assert "created_at" in item

    async def test_list_stories_empty(self, client):
        resp = await client.get("/stories")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"stories": [], "total": 0}


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
