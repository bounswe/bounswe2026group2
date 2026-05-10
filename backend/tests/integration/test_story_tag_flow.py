import uuid

import pytest

from app.services.tag_service import apply_ai_tags_to_story


@pytest.mark.asyncio
class TestStoryTagFlow:
    async def _register_and_login(self, client, username: str, email: str, password: str = "StoryTag1!") -> str:
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def _create_story(self, client, token: str, title: str = "Tagged Story") -> str:
        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": title,
                "content": "Story content about Bogazici and sports in Turkey.",
                "summary": "Tagged summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 2024,
                "date_end": 2024,
            },
        )
        assert resp.status_code == 201
        return resp.json()["id"]

    async def test_apply_ai_tags_persists_and_detail_returns_tags(self, client, db_session):
        token = await self._register_and_login(client, "tagdetail", "tagdetail@example.com")
        story_id = await self._create_story(client, token)

        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(story_id),
            ["  Bogazici ", "Turkiye", "bogazici"],
        )

        resp = await client.get(f"/stories/{story_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] == ["bogazici", "turkiye"]

    async def test_story_listing_search_and_nearby_return_tags(self, client, db_session):
        token = await self._register_and_login(client, "taglist", "taglist@example.com")
        story_id = await self._create_story(client, token, title="Discovery Story")

        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(story_id),
            ["Bogazici", "Spor"],
        )

        list_resp = await client.get("/stories")
        assert list_resp.status_code == 200
        listed = next(story for story in list_resp.json()["stories"] if story["id"] == story_id)
        assert listed["tags"] == ["bogazici", "spor"]

        search_resp = await client.get("/stories/search?place_name=Istanbul")
        assert search_resp.status_code == 200
        searched = next(story for story in search_resp.json()["stories"] if story["id"] == story_id)
        assert searched["tags"] == ["bogazici", "spor"]

        nearby_resp = await client.get("/stories/nearby?lat=41.0082&lng=28.9784&radius_km=5")
        assert nearby_resp.status_code == 200
        nearby = next(story for story in nearby_resp.json()["stories"] if story["id"] == story_id)
        assert nearby["tags"] == ["bogazici", "spor"]

    async def test_saved_stories_returns_tags(self, client, db_session):
        author_token = await self._register_and_login(client, "tagsaveauthor", "tagsaveauthor@example.com")
        saver_token = await self._register_and_login(client, "tagsaver", "tagsaver@example.com")
        story_id = await self._create_story(client, author_token, title="Saved Tagged Story")

        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(story_id),
            ["Turkiye", "Spor"],
        )

        save_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )
        assert save_resp.status_code == 200

        saved_resp = await client.get(
            "/stories/saved",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        assert saved_resp.status_code == 200
        saved_story = next(story for story in saved_resp.json()["stories"] if story["id"] == story_id)
        assert saved_story["tags"] == ["turkiye", "spor"]
