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
