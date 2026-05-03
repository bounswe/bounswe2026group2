import pytest

# Shared credentials for seeded users (set by make_user_entity default password)
ALICE_EMAIL = "seed_alice@example.com"
BOB_EMAIL = "seed_bob@example.com"
SEED_PASSWORD = "ValidPass1!"


@pytest.mark.asyncio
class TestSeededDatabaseContent:
    """Integration tests that verify the seeded_db fixture populates the DB
    correctly and that the data is reachable through the API. Covers #110."""

    async def test_seeded_users_can_log_in(self, client, seeded_db):
        for email in (ALICE_EMAIL, BOB_EMAIL):
            resp = await client.post("/auth/login", json={"email": email, "password": SEED_PASSWORD})
            assert resp.status_code == 200, f"Login failed for {email}: {resp.json()}"
            assert "access_token" in resp.json()

    async def test_three_public_stories_in_listing(self, client, seeded_db):
        resp = await client.get("/stories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3

    async def test_public_story_titles_in_listing(self, client, seeded_db):
        resp = await client.get("/stories")
        assert resp.status_code == 200
        titles = {s["title"] for s in resp.json()["stories"]}
        assert titles == {"Fall of Constantinople", "Atatürk's Ankara", "Ancient Ephesus"}

    async def test_draft_story_excluded_from_listing(self, client, seeded_db):
        resp = await client.get("/stories")
        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()["stories"]]
        assert "Draft Story" not in titles

    async def test_private_story_excluded_from_listing(self, client, seeded_db):
        resp = await client.get("/stories")
        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()["stories"]]
        assert "Private Story" not in titles

    async def test_search_by_place_name_returns_correct_story(self, client, seeded_db):
        resp = await client.get("/stories/search?place_name=Ankara")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Atatürk's Ankara"

    async def test_bounds_filter_returns_istanbul_story(self, client, seeded_db):
        # Tight bounding box around Istanbul (41.0082, 28.9784)
        resp = await client.get(
            "/stories",
            params={
                "min_lat": 40.5,
                "max_lat": 41.5,
                "min_lng": 28.5,
                "max_lng": 29.5,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        titles = [s["title"] for s in data["stories"]]
        assert "Fall of Constantinople" in titles
        assert "Atatürk's Ankara" not in titles
        assert "Ancient Ephesus" not in titles

    async def test_date_filter_returns_stories_in_range(self, client, seeded_db):
        # query 1900–1950 should only return Atatürk's Ankara (1923–1938)
        resp = await client.get(
            "/stories",
            params={"query_start": 1900, "query_end": 1950, "query_precision": "year"},
        )
        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()["stories"]]
        assert "Atatürk's Ankara" in titles
        assert "Fall of Constantinople" not in titles
        assert "Ancient Ephesus" not in titles
