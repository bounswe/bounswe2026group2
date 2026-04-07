import pytest


@pytest.mark.asyncio
class TestStoryTimeOverlapFlow:
    async def _create_user_and_token(self, client):
        await client.post(
            "/auth/register",
            json={
                "username": "timelineuser",
                "email": "timeline@example.com",
                "password": "TimelinePass1!",
            },
        )
        login_resp = await client.post(
            "/auth/login",
            json={
                "email": "timeline@example.com",
                "password": "TimelinePass1!",
            },
        )
        return login_resp.json()["access_token"]

    async def test_year_story_overlaps_date_query(self, client):
        token = await self._create_user_and_token(client)

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Story in 2025",
                "content": "content",
                "summary": "summary",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 2025,
                "date_end": 2025,
            },
        )
        assert create_resp.status_code == 201

        list_resp = await client.get(
            "/stories?query_start=2025-08-01&query_end=2025-08-31&query_precision=date"
        )

        assert list_resp.status_code == 200
        payload = list_resp.json()
        assert payload["total"] == 1
        assert payload["stories"][0]["title"] == "Story in 2025"
