import uuid

import pytest


@pytest.mark.asyncio
class TestStorySaveFlow:
    async def _register_and_login(self, client, username, email, password):
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def _create_story(self, client, token):
        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Savable Story",
                "content": "Story content",
                "summary": "Story summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
                "date_end": 1453,
            },
        )
        assert create_resp.status_code == 201
        return create_resp.json()["id"]

    async def test_authenticated_user_can_save_and_list_story(self, client):
        author_token = await self._register_and_login(
            client, "saveflowauthor", "saveflowauthor@example.com", "FlowPass1!"
        )
        saver_token = await self._register_and_login(client, "saveflowuser", "saveflowuser@example.com", "FlowPass2!")
        story_id = await self._create_story(client, author_token)

        save_resp = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        assert save_resp.status_code == 200
        assert save_resp.json()["saved"] is True

        list_resp = await client.get("/stories/saved", headers={"Authorization": f"Bearer {saver_token}"})

        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["total"] == 1
        assert payload["stories"][0]["id"] == story_id

    async def test_duplicate_save_and_unsave_are_idempotent(self, client):
        author_token = await self._register_and_login(
            client, "saveflowauthor2", "saveflowauthor2@example.com", "FlowPass3!"
        )
        saver_token = await self._register_and_login(client, "saveflowuser2", "saveflowuser2@example.com", "FlowPass4!")
        story_id = await self._create_story(client, author_token)

        first_save = await client.post(
            f"/stories/{story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )
        second_save = await client.post(
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
        list_resp = await client.get("/stories/saved", headers={"Authorization": f"Bearer {saver_token}"})

        assert first_save.status_code == 200
        assert second_save.status_code == 200
        assert first_unsave.status_code == 200
        assert second_unsave.status_code == 200
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 0

    async def test_saved_list_hides_story_after_it_becomes_private(self, client, db_session):
        author_token = await self._register_and_login(
            client, "saveflowauthor3", "saveflowauthor3@example.com", "FlowPass5!"
        )
        saver_token = await self._register_and_login(client, "saveflowuser3", "saveflowuser3@example.com", "FlowPass6!")
        visible_story_id = await self._create_story(client, author_token)
        hidden_story_id = await self._create_story(client, author_token)

        visible_save = await client.post(
            f"/stories/{visible_story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )
        hidden_save = await client.post(
            f"/stories/{hidden_story_id}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        from app.db.enums import StoryVisibility
        from app.db.story import Story

        hidden_story = await db_session.get(Story, uuid.UUID(hidden_story_id))
        hidden_story.visibility = StoryVisibility.PRIVATE
        await db_session.commit()

        list_resp = await client.get("/stories/saved", headers={"Authorization": f"Bearer {saver_token}"})

        assert visible_save.status_code == 200
        assert hidden_save.status_code == 200
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1
        assert list_resp.json()["stories"][0]["id"] == visible_story_id

    async def test_save_missing_story_returns_404(self, client):
        saver_token = await self._register_and_login(client, "saveflowuser4", "saveflowuser4@example.com", "FlowPass7!")

        resp = await client.post(
            f"/stories/{uuid.uuid4()}/save",
            headers={"Authorization": f"Bearer {saver_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"
