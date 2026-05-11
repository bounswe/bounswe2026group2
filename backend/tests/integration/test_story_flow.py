import pytest


@pytest.mark.asyncio
class TestAuthenticatedStoryCreationFlow:
    """Integration test: authenticated user can create a story. Covers #119."""

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

    async def test_authenticated_user_can_create_story(self, client):
        token = await self._register_and_login(client, "storymaker", "storymaker@example.com", "StoryMake1!")

        resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Fall of Constantinople",
                "content": "Detailed account of the 1453 siege.",
                "summary": "The Ottoman conquest of Constantinople.",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
                "date_start": 1453,
                "date_end": 1453,
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Fall of Constantinople"
        assert data["author"] == "storymaker"
        assert data["place_name"] == "Istanbul"
        assert data["date_start"] == "1453-01-01"
        assert data["date_end"] == "1453-12-31"
        assert data["date_precision"] == "year"
        assert data["status"] == "published"
        assert data["visibility"] == "public"
        assert "id" in data

    async def test_created_story_appears_in_listing(self, client):
        token = await self._register_and_login(client, "listcheck", "listcheck@example.com", "ListCheck1!")

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Visible Story",
                "content": "Some content",
                "summary": "Short summary",
                "place_name": "Ankara",
                "latitude": 39.9334,
                "longitude": 32.8597,
                "date_start": 1923,
                "date_end": 1923,
            },
        )
        assert create_resp.status_code == 201

        list_resp = await client.get("/stories")
        assert list_resp.status_code == 200
        titles = [s["title"] for s in list_resp.json()["stories"]]
        assert "Visible Story" in titles


@pytest.mark.asyncio
class TestUnauthenticatedStoryCreationRejectionFlow:
    """Integration test: unauthenticated story creation is rejected. Covers #121."""

    async def test_unauthenticated_request_returns_401(self, client):
        resp = await client.post(
            "/stories",
            json={
                "title": "Unauthorized Story",
                "content": "Should be rejected.",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 401

    async def test_invalid_token_returns_401(self, client):
        resp = await client.post(
            "/stories",
            headers={"Authorization": "Bearer not-a-real-token"},
            json={
                "title": "Bad Token Story",
                "content": "Should be rejected.",
                "place_name": "Istanbul",
                "latitude": 41.0082,
                "longitude": 28.9784,
            },
        )

        assert resp.status_code == 401

    async def test_unauthenticated_story_not_stored(self, client):
        await client.post(
            "/stories",
            json={
                "title": "Ghost Story",
                "content": "Should never be saved.",
                "place_name": "Izmir",
                "latitude": 38.4192,
                "longitude": 27.1287,
            },
        )

        list_resp = await client.get("/stories")
        assert list_resp.status_code == 200
        titles = [s["title"] for s in list_resp.json()["stories"]]
        assert "Ghost Story" not in titles


@pytest.mark.asyncio
class TestStoryRetrievalByIDFlow:
    """Integration test: story retrieval by ID. Covers #145."""

    async def _create_story(self, client):
        await client.post(
            "/auth/register",
            json={"username": "retriever", "email": "retriever@example.com", "password": "Retrieve1!"},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "retriever@example.com", "password": "Retrieve1!"},
        )
        token = login_resp.json()["access_token"]

        create_resp = await client.post(
            "/stories",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "title": "Retrievable Story",
                "content": "Full story content here.",
                "summary": "Summary here.",
                "place_name": "Bursa",
                "latitude": 40.1826,
                "longitude": 29.0665,
                "date_start": 1326,
                "date_end": 1326,
            },
        )
        assert create_resp.status_code == 201
        return create_resp.json()

    async def test_retrieve_story_by_id_returns_correct_data(self, client):
        created = await self._create_story(client)
        story_id = created["id"]

        resp = await client.get(f"/stories/{story_id}")

        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == story_id
        assert data["title"] == "Retrievable Story"
        assert data["content"] == "Full story content here."
        assert data["summary"] == "Summary here."
        assert data["author"] == "retriever"
        assert data["place_name"] == "Bursa"
        assert data["date_start"] == "1326-01-01"
        assert data["date_end"] == "1326-12-31"
        assert data["date_precision"] == "year"
        assert "media_files" in data

    async def test_retrieve_nonexistent_story_returns_404(self, client):
        import uuid

        resp = await client.get(f"/stories/{uuid.uuid4()}")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Story not found"


@pytest.mark.asyncio
class TestStorySearchByPlaceNameFlow:
    """Integration test: story search by place name. Covers #146."""

    async def _seed_stories(self, client):
        await client.post(
            "/auth/register",
            json={"username": "placeseed", "email": "placeseed@example.com", "password": "PlaceSeed1!"},
        )
        login_resp = await client.post(
            "/auth/login",
            json={"email": "placeseed@example.com", "password": "PlaceSeed1!"},
        )
        token = login_resp.json()["access_token"]

        for title, place, lat, lng in [
            ("Istanbul Story", "Istanbul", 41.0082, 28.9784),
            ("Ankara Story", "Ankara", 39.9334, 32.8597),
        ]:
            resp = await client.post(
                "/stories",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "title": title,
                    "content": f"Content about {place}",
                    "summary": f"About {place}",
                    "place_name": place,
                    "latitude": lat,
                    "longitude": lng,
                    "date_start": 1900,
                    "date_end": 1900,
                },
            )
            assert resp.status_code == 201

    async def test_search_returns_matching_place(self, client):
        await self._seed_stories(client)

        resp = await client.get("/stories/search?place_name=Istanbul")

        assert resp.status_code == 200
        data = resp.json()
        titles = [story["title"] for story in data["stories"]]
        assert "Istanbul Story" in titles
        assert data["stories"][0]["place_name"] == "Istanbul"

    async def test_search_q_returns_matching_story_content(self, client):
        await self._seed_stories(client)

        resp = await client.get("/stories/search?q=Content%20about%20Istanbul")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Istanbul Story"

    async def test_search_q_returns_matching_story_content_with_typo(self, client):
        await self._seed_stories(client)

        resp = await client.get("/stories/search?q=Istanubl")

        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["stories"][0]["title"] == "Istanbul Story"

    async def test_search_excludes_non_matching_place(self, client):
        await self._seed_stories(client)

        resp = await client.get("/stories/search?place_name=Istanbul")

        assert resp.status_code == 200
        titles = [s["title"] for s in resp.json()["stories"]]
        assert "Ankara Story" not in titles

    async def test_search_no_match_returns_empty(self, client):
        await self._seed_stories(client)

        resp = await client.get("/stories/search?place_name=Trabzon")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"stories": [], "total": 0}

    async def test_search_q_no_match_returns_empty(self, client):
        await self._seed_stories(client)

        resp = await client.get("/stories/search?q=Trabzon")

        assert resp.status_code == 200
        data = resp.json()
        assert data == {"stories": [], "total": 0}

    async def test_search_missing_place_name_returns_422(self, client):
        resp = await client.get("/stories/search")

        assert resp.status_code == 400
