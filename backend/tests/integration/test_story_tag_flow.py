import asyncio
import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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

    async def test_story_listing_filters_by_tags_with_or_matching_and_relevance_ranking(self, client, db_session):
        token = await self._register_and_login(client, "tagfilter", "tagfilter@example.com")
        multi_tag_story_id = await self._create_story(client, token, title="Sport History Story")
        single_tag_story_id = await self._create_story(client, token, title="Sport Story")
        non_matching_story_id = await self._create_story(client, token, title="Music Story")

        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(multi_tag_story_id),
            ["Spor", "Tarih"],
        )
        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(single_tag_story_id),
            ["Spor"],
        )
        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(non_matching_story_id),
            ["Muzik"],
        )

        resp = await client.get("/stories?tags=spor&tags=tarih")

        assert resp.status_code == 200
        titles = [story["title"] for story in resp.json()["stories"]]
        assert titles == ["Sport History Story", "Sport Story"]

    async def test_story_search_filters_by_place_and_tags_with_relevance_ranking(self, client, db_session):
        token = await self._register_and_login(client, "tagsearch", "tagsearch@example.com")
        multi_tag_story_id = await self._create_story(client, token, title="Istanbul Sport History Story")
        single_tag_story_id = await self._create_story(client, token, title="Istanbul Sport Story")

        ankara_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Ankara Sport History Story",
                "content": "Story content about sports history in Ankara.",
                "summary": "Tagged Ankara summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "date_start": 2024,
                "date_end": 2024,
            },
        )
        assert ankara_resp.status_code == 201
        ankara_story_id = ankara_resp.json()["id"]

        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(multi_tag_story_id),
            ["Spor", "Tarih"],
        )
        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(single_tag_story_id),
            ["Spor"],
        )
        await apply_ai_tags_to_story(
            db_session,
            uuid.UUID(ankara_story_id),
            ["Spor", "Tarih"],
        )

        resp = await client.get("/stories/search?place_name=Istanbul&tags=spor&tags=tarih")

        assert resp.status_code == 200
        titles = [story["title"] for story in resp.json()["stories"]]
        assert titles == ["Istanbul Sport History Story", "Istanbul Sport Story"]

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


@pytest.mark.asyncio
class TestStoryAiTaggingBackgroundFlow:
    def _patch_background_session_factory(self, monkeypatch, db_session):
        session_factory = async_sessionmaker(
            bind=db_session.bind,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        monkeypatch.setattr("app.services.ai_tagging_system.AsyncSessionLocal", session_factory)
        monkeypatch.setattr("app.services.transcription_service.AsyncSessionLocal", session_factory)

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

    async def _wait_for_story_tags(self, client, story_id: str, expected_tags: list[str]) -> dict:
        for _ in range(10):
            detail_resp = await client.get(f"/stories/{story_id}")
            assert detail_resp.status_code == 200
            data = detail_resp.json()
            if data["tags"] == expected_tags:
                return data
            await asyncio.sleep(0.1)

        return data

    async def test_create_story_triggers_background_ai_tagging(self, client, db_session, monkeypatch):
        self._patch_background_session_factory(monkeypatch, db_session)
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.routers.story.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr(
            "app.services.ai_tagging_system.generate_ai_story_tags",
            AsyncMock(return_value=["bogazici", "turkiye", "spor"]),
        )

        token = await self._register_and_login(client, "autotag1", "autotag1@example.com")
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Background Tagged Story",
                "content": "A story about Bogazici sports memories in Turkey.",
                "summary": "Auto-tag this story",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 2024,
                "date_end": 2024,
            },
        )

        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        data = await self._wait_for_story_tags(client, story_id, ["bogazici", "turkiye", "spor"])
        assert data["tags"] == ["bogazici", "turkiye", "spor"]

    async def test_ai_tagging_failure_does_not_break_story_creation(self, client, db_session, monkeypatch):
        self._patch_background_session_factory(monkeypatch, db_session)
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.routers.story.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr(
            "app.services.ai_tagging_system.generate_ai_story_tags",
            AsyncMock(side_effect=RuntimeError("ai down")),
        )

        token = await self._register_and_login(client, "autotag2", "autotag2@example.com")
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Story Still Creates",
                "content": "Even if AI tagging fails, creation should succeed.",
                "summary": "Failure-tolerant creation",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "date_start": 2024,
                "date_end": 2024,
            },
        )

        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["tags"] == []

    async def test_audio_transcript_completion_triggers_ai_tagging(self, client, db_session, monkeypatch):
        self._patch_background_session_factory(monkeypatch, db_session)
        monkeypatch.setattr("app.services.story_service.upload_bytes", lambda **kwargs: None)
        monkeypatch.setattr("app.services.ai_tagging_system.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.routers.story.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr("app.services.transcription_service.is_ai_tagging_configured", lambda: True)
        monkeypatch.setattr(
            "app.services.transcription_service.transcribe_audio_content",
            AsyncMock(return_value="Bosphorus running memories and local sports narration"),
        )
        monkeypatch.setattr(
            "app.services.ai_tagging_system.generate_ai_story_tags",
            AsyncMock(side_effect=[["story"], ["story", "audio", "bosphorus"]]),
        )

        token = await self._register_and_login(client, "autotag3", "autotag3@example.com")
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Audio Tagged Story",
                "content": "Initial story content.",
                "summary": "Audio story",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 2024,
                "date_end": 2024,
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        upload_resp = await client.post(
            f"/stories/{story_id}/media",
            headers={"Authorization": f"Bearer {token}"},
            data={"media_type": "audio", "sort_order": "0"},
            files={"file": ("audio.webm", b"audio-bytes", "audio/webm")},
        )
        assert upload_resp.status_code == 201

        data = await self._wait_for_story_tags(client, story_id, ["story", "audio", "bosphorus"])
        assert data["media_files"][0]["transcript"] == "Bosphorus running memories and local sports narration"
        assert data["tags"] == ["story", "audio", "bosphorus"]
