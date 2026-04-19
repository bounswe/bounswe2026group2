import uuid

import pytest


@pytest.mark.asyncio
class TestStoryLikeFlow:
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
                "title": "Likable Story",
                "content": "Content for likes",
                "summary": "Summary for likes",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
                "date_end": 1453,
            },
        )
        assert create_resp.status_code == 201
        return create_resp.json()["id"]

    async def test_authenticated_user_can_like_story_and_see_detail_count(self, client):
        author_token = await self._register_and_login(client, "likeauthor", "likeauthor@example.com", "LikeAuth1!")
        liker_token = await self._register_and_login(client, "likeruser", "liker@example.com", "LikeUser1!")
        story_id = await self._create_story(client, author_token)

        like_resp = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert like_resp.status_code == 200
        assert like_resp.json() == {
            "story_id": story_id,
            "liked": True,
            "like_count": 1,
        }

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["like_count"] == 1

    async def test_duplicate_like_and_duplicate_unlike_are_idempotent(self, client):
        author_token = await self._register_and_login(client, "likeauthor2", "likeauthor2@example.com", "LikeAuth2!")
        liker_token = await self._register_and_login(client, "likeruser2", "liker2@example.com", "LikeUser2!")
        story_id = await self._create_story(client, author_token)

        first_like = await client.post(
            f"/stories/{story_id}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )
        second_like = await client.post(
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

        assert first_like.status_code == 200
        assert second_like.status_code == 200
        assert first_like.json()["like_count"] == 1
        assert second_like.json()["like_count"] == 1
        assert first_unlike.status_code == 200
        assert second_unlike.status_code == 200
        assert first_unlike.json()["like_count"] == 0
        assert second_unlike.json()["like_count"] == 0

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        assert detail_resp.json()["like_count"] == 0

    async def test_like_missing_story_returns_404(self, client):
        liker_token = await self._register_and_login(client, "likeruser3", "liker3@example.com", "LikeUser3!")

        resp = await client.post(
            f"/stories/{uuid.uuid4()}/like",
            headers={"Authorization": f"Bearer {liker_token}"},
        )

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"
