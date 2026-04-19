import uuid

import pytest


@pytest.mark.asyncio
class TestStoryCommentFlow:
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
                "title": "Commentable Story",
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

    async def test_authenticated_user_can_create_comment_and_list_it(self, client):
        author_token = await self._register_and_login(client, "commentflowauthor", "commentflowauthor@example.com", "FlowPass1!")
        commenter_token = await self._register_and_login(client, "commentflowuser", "commentflowuser@example.com", "FlowPass2!")
        story_id = await self._create_story(client, author_token)

        create_comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "Wonderful context"},
        )

        assert create_comment_resp.status_code == 201
        assert create_comment_resp.json()["author"]["username"] == "commentflowuser"

        list_comments_resp = await client.get(f"/stories/{story_id}/comments")

        assert list_comments_resp.status_code == 200
        payload = list_comments_resp.json()
        assert payload["total"] == 1
        assert payload["comments"][0]["content"] == "Wonderful context"

    async def test_unauthenticated_comment_creation_is_rejected(self, client):
        token = await self._register_and_login(client, "commentflowauthor2", "commentflowauthor2@example.com", "FlowPass3!")
        story_id = await self._create_story(client, token)

        resp = await client.post(
            f"/stories/{story_id}/comments",
            json={"content": "Should be rejected"},
        )

        assert resp.status_code == 401

    async def test_comment_endpoints_return_404_for_missing_story(self, client):
        commenter_token = await self._register_and_login(client, "commentflowuser2", "commentflowuser2@example.com", "FlowPass4!")
        missing_story_id = uuid.uuid4()

        create_resp = await client.post(
            f"/stories/{missing_story_id}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "Hello"},
        )
        list_resp = await client.get(f"/stories/{missing_story_id}/comments")

        assert create_resp.status_code == 404
        assert list_resp.status_code == 404

    async def test_comment_owner_can_delete_comment(self, client):
        author_token = await self._register_and_login(client, "commentflowauthor3", "commentflowauthor3@example.com", "FlowPass5!")
        commenter_token = await self._register_and_login(client, "commentflowuser3", "commentflowuser3@example.com", "FlowPass6!")
        story_id = await self._create_story(client, author_token)

        create_comment_resp = await client.post(
            f"/stories/{story_id}/comments",
            headers={"Authorization": f"Bearer {commenter_token}"},
            json={"content": "Temporary comment"},
        )
        comment_id = create_comment_resp.json()["id"]

        delete_resp = await client.delete(
            f"/stories/{story_id}/comments/{comment_id}",
            headers={"Authorization": f"Bearer {commenter_token}"},
        )
        list_resp = await client.get(f"/stories/{story_id}/comments")

        assert delete_resp.status_code == 204
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 0
