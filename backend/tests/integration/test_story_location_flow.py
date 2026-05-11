import pytest


@pytest.mark.asyncio
class TestStoryLocationFlow:
    """Integration tests for multi-location story support. Covers #231."""

    async def _register_and_login(self, client, username: str, email: str, password: str = "Locate1!A") -> str:
        await client.post(
            "/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        return login_resp.json()["access_token"]

    async def test_create_story_with_locations_returns_locations_in_detail(self, client):
        token = await self._register_and_login(client, "loccreator", "loccreator@example.com")

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Silk Road Journey",
                "content": "A journey along the ancient Silk Road.",
                "summary": "Multi-stop trade route story.",
                "place_name": "Samarkand",
                "latitude": 39.6542,
                "longitude": 66.9597,
                "date_start": 1200,
                "date_end": 1300,
                "locations": [
                    {"latitude": 39.6542, "longitude": 66.9597, "label": "Samarkand"},
                    {"latitude": 41.2995, "longitude": 69.2401, "label": "Tashkent"},
                    {"latitude": 37.9601, "longitude": 58.3261, "label": "Merv"},
                ],
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        story_id = data["id"]

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        assert len(detail["locations"]) == 3
        labels = [loc["label"] for loc in detail["locations"]]
        assert labels == ["Samarkand", "Tashkent", "Merv"]

        coords = [(loc["latitude"], loc["longitude"]) for loc in detail["locations"]]
        assert (39.6542, 66.9597) in coords
        assert (41.2995, 69.2401) in coords

        for i, loc in enumerate(detail["locations"]):
            assert loc["sort_order"] == i

    async def test_create_story_without_locations_defaults_to_primary(self, client):
        token = await self._register_and_login(client, "locdefault", "locdefault@example.com")

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Single Point Story",
                "content": "Story with only the primary location.",
                "summary": "One place story.",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 201
        story_id = resp.json()["id"]

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        assert len(detail["locations"]) == 1
        loc = detail["locations"][0]
        assert loc["latitude"] == 41.0082
        assert loc["longitude"] == 28.9784
        assert loc["sort_order"] == 0

    async def test_update_story_replaces_locations(self, client):
        token = await self._register_and_login(client, "locupdater", "locupdater@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Updateable Story",
                "content": "Initial content.",
                "summary": "Initial summary.",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "locations": [
                    {"latitude": 39.9334, "longitude": 32.8597, "label": "Ankara"},
                ],
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        update_resp = await client.put(
            f"/stories/{story_id}",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Updateable Story",
                "content": "Updated content.",
                "summary": "Updated summary.",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "locations": [
                    {"latitude": 39.9334, "longitude": 32.8597, "label": "Ankara"},
                    {"latitude": 40.1826, "longitude": 29.0665, "label": "Bursa"},
                ],
            },
        )
        assert update_resp.status_code == 200

        detail_resp = await client.get(f"/stories/{story_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()

        assert len(detail["locations"]) == 2
        labels = [loc["label"] for loc in detail["locations"]]
        assert "Ankara" in labels
        assert "Bursa" in labels

    async def test_create_story_with_duplicate_locations_returns_422(self, client):
        token = await self._register_and_login(client, "locduplicate", "locduplicate@example.com")

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Duplicate Locations Story",
                "content": "Some content.",
                "summary": "Should fail.",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "locations": [
                    {"latitude": 41.0082, "longitude": 28.9784, "label": "Istanbul"},
                    {"latitude": 41.0082, "longitude": 28.9784, "label": "Istanbul Again"},
                ],
            },
        )

        assert resp.status_code == 422

    async def test_bounds_filter_matches_story_via_secondary_location(self, client):
        token = await self._register_and_login(client, "locbounds", "locbounds@example.com")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Route Through Izmir",
                "content": "A story that passes through Izmir.",
                "summary": "Multi-city route.",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "locations": [
                    {"latitude": 41.0082, "longitude": 28.9784, "label": "Istanbul"},
                    {"latitude": 38.4192, "longitude": 27.1287, "label": "Izmir"},
                ],
            },
        )
        assert create_resp.status_code == 201
        story_id = create_resp.json()["id"]

        # Search bounds that only cover Izmir (secondary location), not Istanbul (primary)
        search_resp = await client.get(
            "/stories",
            params={
                "min_lat": 37.0,
                "max_lat": 39.5,
                "min_lng": 26.0,
                "max_lng": 28.5,
            },
        )
        assert search_resp.status_code == 200
        ids = [s["id"] for s in search_resp.json()["stories"]]
        assert story_id in ids
