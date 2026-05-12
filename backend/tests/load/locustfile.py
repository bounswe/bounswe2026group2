"""Locust load test for Local History Map API.

Install:  pip3 install locust
Run:      locust -f locustfile.py --host http://localhost:8000
Then open http://localhost:8089 to start a test run.

Headless example (100 users, 10 spawn/s, 60 s):
    locust -f locustfile.py --host http://localhost:8000 \
           --users 100 --spawn-rate 10 --run-time 60s --headless

Endpoints exercised (weighted by real-world read:write ratio):
  50%  GET  /stories               — public story list
  20%  GET  /stories/search        — place-name search
  15%  GET  /stories/{id}          — story detail
  10%  GET  /auth/me               — authenticated token validation
   5%  POST /auth/login            — login (write path)
"""

import random

from locust import HttpUser, between, task

# Seed place names that match the seeded_db fixture data.
PLACE_NAMES = [
    "Istanbul",
    "Ankara",
    "Bosphorus",
    "Galata",
    "Topkapi",
    "Beşiktaş",
    "Kapadokya",
    "Troy",
]

# Credentials that exist in the seeded_db fixture.
SEED_USERS = [
    {"username": "alice", "password": "alice_password123!"},
    {"username": "bob", "password": "bob_password123!"},
]


class StoryMapUser(HttpUser):
    """Simulates a typical user browsing and searching stories."""

    wait_time = between(0.5, 2.0)

    def on_start(self) -> None:
        """Log in once at the start of each simulated user session."""
        creds = random.choice(SEED_USERS)
        resp = self.client.post(
            "/auth/login",
            json={"username": creds["username"], "password": creds["password"]},
            name="/auth/login [setup]",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token", "")
        else:
            self._token = ""
        self._story_ids: list[str] = []

    def _auth_headers(self) -> dict:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    @task(50)
    def list_stories(self) -> None:
        resp = self.client.get("/stories", name="/stories")
        if resp.status_code == 200:
            stories = resp.json().get("stories", [])
            # Cache IDs for the detail task so we hit real rows.
            for s in stories[:5]:
                sid = s.get("id")
                if sid and sid not in self._story_ids:
                    self._story_ids.append(sid)

    @task(20)
    def search_stories(self) -> None:
        place = random.choice(PLACE_NAMES)
        self.client.get(f"/stories/search?place_name={place}", name="/stories/search")

    @task(15)
    def story_detail(self) -> None:
        if not self._story_ids:
            self.list_stories()
            return
        story_id = random.choice(self._story_ids)
        self.client.get(f"/stories/{story_id}", name="/stories/{id}")

    @task(10)
    def auth_me(self) -> None:
        self.client.get("/auth/me", headers=self._auth_headers(), name="/auth/me")

    @task(5)
    def login(self) -> None:
        creds = random.choice(SEED_USERS)
        self.client.post(
            "/auth/login",
            json={"username": creds["username"], "password": creds["password"]},
            name="/auth/login",
        )
