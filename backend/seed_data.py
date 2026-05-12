#!/usr/bin/env python3
"""
seed_data.py — Populate Local History Story Map with realistic demo data.

Run while Docker is up:
    docker compose exec backend python3 seed_data.py

Or against a locally running backend:
    DATABASE_URL=postgresql://postgres:postgres@localhost:5432/localhistory \\
    SEED_API_URL=http://127.0.0.1:8000 python3 backend/seed_data.py

Accounts created
----------------
  admin  / Admin123!   (role: admin)
  alice  / Alice123!   (role: user)
  bob    / Bobbb123!   (role: user)
  charlie / Charlie123! (role: user)

Stories created (all public & published unless noted)
------------------------------------------------------
  1. Fall of Constantinople          — alice, Istanbul, year 1453, tags: history ottoman byzantine  [+ image attachment]
  2. Battle of Gallipoli             — alice, Gallipoli, date 1915-04-25→1915-12-20, tags: history modern
  3. The Silk Road Through Anatolia  — bob, MULTI-LOCATION (Istanbul/Ankara/Konya), year 1200, tags: ancient history
  4. A Witness to History (anon)     — bob, anonymous, Istanbul, year 1900, tags: modern
  5. Atatürk's Ankara                — admin, Ankara, date 1923-10-29→1923-10-29, tags: history modern
  6. Hagia Sophia Through the Ages   — alice, Istanbul, date 0537-02-15→1453-05-29, tags: byzantine ancient
  7. Urban Legends of Istanbul       — charlie, Istanbul, no date, tags: history
  8. Draft Story (private)           — charlie, DRAFT / PRIVATE (won't appear in public listing)
"""

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

import asyncpg

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = os.environ.get("SEED_API_URL", "http://127.0.0.1:8000")

_raw_db_url = os.environ.get(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/localhistory",
)
# asyncpg uses postgresql:// not postgresql+asyncpg://
DB_DSN = _raw_db_url.replace("postgresql+asyncpg://", "postgresql://")

# 1×1 white PNG — used as a placeholder image attachment
_TINY_PNG = bytes([
    0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
    0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
    0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
    0x08, 0x02, 0x00, 0x00, 0x00, 0x90, 0x77, 0x53,
    0xDE, 0x00, 0x00, 0x00, 0x0C, 0x49, 0x44, 0x41,
    0x54, 0x08, 0xD7, 0x63, 0xF8, 0xCF, 0xC0, 0x00,
    0x00, 0x00, 0x02, 0x00, 0x01, 0xE2, 0x21, 0xBC,
    0x33, 0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E,
    0x44, 0xAE, 0x42, 0x60, 0x82,
])


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _api(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    url = BASE_URL + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"{method} {path} → {exc.code}: {detail}") from exc


def _upload_image(path: str, token: str, file_bytes: bytes, filename: str, alt_text: str) -> dict:
    """POST multipart/form-data with a file field named 'file'."""
    boundary = "SeedDataBoundary42"

    def _field(name: str, value: str) -> bytes:
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()

    body = (
        _field("media_type", "image")
        + _field("alt_text", alt_text)
        + _field("caption", "Seeded demo image")
        + f"--{boundary}\r\n".encode()
        + f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode()
        + b"Content-Type: image/png\r\n\r\n"
        + file_bytes
        + f"\r\n--{boundary}--\r\n".encode()
    )

    url = BASE_URL + path
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        print(f"  [WARN] image upload failed ({exc.code}): {detail[:200]}")
        return {}


def _register(username: str, email: str, password: str) -> None:
    try:
        _api("POST", "/auth/register", {
            "username": username,
            "email": email,
            "password": password,
        })
        print(f"  Registered {username}")
    except RuntimeError as exc:
        if "409" in str(exc):
            print(f"  {username} already exists — skipping registration")
        else:
            raise


def _login(email: str, password: str) -> str:
    resp = _api("POST", "/auth/login", {"email": email, "password": password})
    return resp["access_token"]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

async def _ensure_password(email: str, password: str) -> None:
    """Force-update password_hash for a user — makes the script idempotent."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    new_hash = pwd_context.hash(password)
    conn = await asyncpg.connect(DB_DSN)
    try:
        await conn.execute(
            "UPDATE users SET password_hash = $1 WHERE email = $2",
            new_hash,
            email,
        )
    finally:
        await conn.close()


async def _set_admin_role(username: str) -> None:
    conn = await asyncpg.connect(DB_DSN)
    try:
        updated = await conn.fetchval(
            "UPDATE users SET role = 'ADMIN' WHERE username = $1 RETURNING id",
            username,
        )
        if updated:
            print(f"  Set role=admin for '{username}'")
        else:
            print(f"  [WARN] user '{username}' not found in DB — admin role not set")
    finally:
        await conn.close()


async def _set_story_draft(story_id: str) -> None:
    conn = await asyncpg.connect(DB_DSN)
    try:
        import uuid as _uuid
        await conn.execute(
            "UPDATE stories SET status = 'DRAFT', visibility = 'PRIVATE' WHERE id = $1",
            _uuid.UUID(story_id),
        )
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Story creation helpers
# ---------------------------------------------------------------------------

def _create_story(token: str, payload: dict) -> dict:
    return _api("POST", "/stories", payload, token=token)


def _like(token: str, story_id: str) -> None:
    _api("POST", f"/stories/{story_id}/like", token=token)


def _comment(token: str, story_id: str, text: str) -> None:
    _api("POST", f"/stories/{story_id}/comments", {"content": text}, token=token)


def _save(token: str, story_id: str) -> None:
    _api("POST", f"/stories/{story_id}/save", token=token)


# ---------------------------------------------------------------------------
# Main seed routine
# ---------------------------------------------------------------------------

def seed() -> None:
    print(f"\n=== Seeding {BASE_URL} ===\n")

    # ── 1. Register users (idempotent: force-reset passwords if already existing)
    print("── Users ──")
    _USERS = [
        ("admin",   "admin@localhistory.app", "Admin123!"),
        ("alice",   "alice@example.com",      "Alice123!"),
        ("bob",     "bob@example.com",         "Bobbb123!"),
        ("charlie", "charlie@example.com",     "Charlie123!"),
    ]
    for username, email, password in _USERS:
        _register(username, email, password)
        asyncio.run(_ensure_password(email, password))

    # ── 2. Promote admin via direct DB update ────────────────────────────────
    asyncio.run(_set_admin_role("admin"))

    # ── 3. Login all users ───────────────────────────────────────────────────
    tok_admin   = _login("admin@localhistory.app", "Admin123!")
    tok_alice   = _login("alice@example.com",      "Alice123!")
    tok_bob     = _login("bob@example.com",         "Bobbb123!")
    tok_charlie = _login("charlie@example.com",     "Charlie123!")
    print("  All users logged in\n")

    # ── 4. Create stories ────────────────────────────────────────────────────
    print("── Stories ──")

    # 4a. Single-location, year precision (alice)
    story_cpl = _create_story(tok_alice, {
        "title": "Fall of Constantinople",
        "summary": "The 1453 Ottoman siege that ended the Byzantine Empire.",
        "content": (
            "On 29 May 1453, Sultan Mehmed II's forces breached the Theodosian Walls "
            "after a 53-day siege. The fall ended over a thousand years of Byzantine "
            "rule and marked the end of the Middle Ages for many historians. The Hagia "
            "Sophia was converted into a mosque, and Constantinople was renamed Istanbul, "
            "becoming the new capital of the Ottoman Empire."
        ),
        "place_name": "Constantinople (Istanbul)",
        "latitude": 41.0082,
        "longitude": 28.9784,
        "date_start": 1453,
        "date_end": 1453,
        "tags": ["history", "ottoman", "byzantine"],
    })
    print(f"  Created: {story_cpl['title']}  (id={story_cpl['id'][:8]}…)")

    # Attach a placeholder image to this story
    _upload_image(
        f"/stories/{story_cpl['id']}/media",
        tok_alice,
        _TINY_PNG,
        "constantinople.png",
        "Panoramic view of Constantinople walls",
    )
    print("  Uploaded placeholder image to 'Fall of Constantinople'")

    # 4b. Single-location, date precision (alice)
    story_gallipoli = _create_story(tok_alice, {
        "title": "Battle of Gallipoli",
        "summary": "The WWI Dardanelles campaign that shaped modern Turkey and ANZAC identity.",
        "content": (
            "From 25 April 1915 to 9 January 1916, Allied forces attempted to seize the "
            "Gallipoli Peninsula to open the Dardanelles strait. The campaign ended in "
            "Ottoman victory, but the bravery shown by ANZAC (Australian and New Zealand "
            "Army Corps) troops became a defining moment of national identity. Mustafa Kemal "
            "— later Atatürk — rose to prominence commanding the Ottoman defense."
        ),
        "place_name": "Gallipoli Peninsula",
        "latitude": 40.3427,
        "longitude": 26.6717,
        "date_start": "1915-04-25",
        "date_end": "1915-12-20",
        "date_precision": "date",
        "tags": ["history", "modern"],
    })
    print(f"  Created: {story_gallipoli['title']}  (id={story_gallipoli['id'][:8]}…)")

    # 4c. Multi-location story (bob)
    story_silkroad = _create_story(tok_bob, {
        "title": "The Silk Road Through Anatolia",
        "summary": "How medieval trade routes connected East and West across modern Turkey.",
        "content": (
            "During the 12th–13th centuries, Anatolian Seljuk sultans built a network of "
            "caravanserais — fortified roadside inns — every 30–40 km along Silk Road routes. "
            "Merchants traveling between Istanbul (Constantinople), Konya, and Central Asia "
            "could rest, resupply, and trade safely. The route through Ankara served as a "
            "crucial mid-point, linking the Byzantine coastal markets to the Seljuk heartland "
            "in Konya. Goods included silk, spices, ceramics, glass, and precious metals."
        ),
        "place_name": "Anatolia",
        "latitude": 39.9334,
        "longitude": 32.8597,
        "date_start": 1200,
        "date_end": 1300,
        "tags": ["ancient", "history"],
        "locations": [
            {"latitude": 41.0082, "longitude": 28.9784, "label": "Constantinople (Istanbul) — western terminus"},
            {"latitude": 39.9334, "longitude": 32.8597, "label": "Ankara — central hub"},
            {"latitude": 37.8714, "longitude": 32.4846, "label": "Konya — Seljuk capital"},
        ],
    })
    print(f"  Created: {story_silkroad['title']}  (multi-location, id={story_silkroad['id'][:8]}…)")

    # 4d. Anonymous story (bob)
    story_anon = _create_story(tok_bob, {
        "title": "A Witness to History",
        "summary": "A personal account of living through the end of the Ottoman era.",
        "content": (
            "I was a child when the empire began to crumble. I remember the sound of cannon "
            "fire in the distance, the smell of bread my grandmother baked while the adults "
            "whispered of war. The old neighborhoods changed faster than anyone could have "
            "imagined — mosques converted, street signs repainted, old faces gone. Some things "
            "are too painful to attach a name to."
        ),
        "place_name": "Istanbul",
        "latitude": 41.0082,
        "longitude": 28.9784,
        "date_start": 1900,
        "date_end": 1930,
        "tags": ["modern"],
        "is_anonymous": True,
    })
    print(f"  Created: {story_anon['title']}  (anonymous, id={story_anon['id'][:8]}…)")

    # 4e. Admin-owned story
    story_ataturk = _create_story(tok_admin, {
        "title": "Atatürk's Ankara: Birth of a Capital",
        "summary": "How Ankara was chosen as the capital of the new Turkish Republic.",
        "content": (
            "On 29 October 1923, Mustafa Kemal Atatürk proclaimed the Republic of Turkey "
            "with Ankara as its capital — a deliberate break from the Ottoman past centered "
            "on Istanbul. Ankara had been a modest Anatolian city, but its central location "
            "made it strategically ideal during the War of Independence. Grand Assembly "
            "buildings, boulevards, and Western-style universities were constructed rapidly, "
            "transforming the small city into a modern capital within a decade."
        ),
        "place_name": "Ankara",
        "latitude": 39.9334,
        "longitude": 32.8597,
        "date_start": "1923-10-29",
        "date_end": "1923-10-29",
        "date_precision": "date",
        "tags": ["history", "modern"],
    })
    print(f"  Created: {story_ataturk['title']}  (admin-owned, id={story_ataturk['id'][:8]}…)")

    # 4f. Very old date precision story (alice)
    story_hagia = _create_story(tok_alice, {
        "title": "Hagia Sophia Through the Ages",
        "summary": "From Byzantine cathedral to Ottoman mosque to museum — and back.",
        "content": (
            "Built under Emperor Justinian I and consecrated on 27 December 537, the Hagia "
            "Sophia served as the world's largest cathedral for nearly a thousand years. After "
            "the Ottoman conquest of 1453, it was converted into a mosque. In 1934, Atatürk "
            "secularized it as a museum. In 2020 it returned to mosque status. The building "
            "witnessed the crowning of Byzantine emperors, the first Friday prayers of the "
            "Ottoman era, and countless pivotal moments in Mediterranean history."
        ),
        "place_name": "Hagia Sophia, Istanbul",
        "latitude": 41.0086,
        "longitude": 28.9802,
        "date_start": "0537-02-15",
        "date_end": "1453-05-29",
        "date_precision": "date",
        "tags": ["byzantine", "ancient"],
    })
    print(f"  Created: {story_hagia['title']}  (id={story_hagia['id'][:8]}…)")

    # 4g. No date story (charlie)
    story_legends = _create_story(tok_charlie, {
        "title": "Urban Legends of Istanbul",
        "summary": "The folklore and ghost stories that haunt Istanbul's ancient streets.",
        "content": (
            "Every neighborhood of Istanbul has its legends. The covered bazaar hides a "
            "vault that no locksmith has ever opened. The Basilica Cistern is said to have "
            "a mirror column that grants wishes to those who press their thumb into its "
            "carved surface. Eyüp's old cemetery is avoided after dark. These stories, passed "
            "from grandmother to grandchild, are as much a part of the city's fabric as its "
            "minarets and bridges."
        ),
        "place_name": "Istanbul",
        "latitude": 41.0082,
        "longitude": 28.9784,
        "tags": ["history"],
    })
    print(f"  Created: {story_legends['title']}  (no date, id={story_legends['id'][:8]}…)")

    # 4h. Draft/private story (charlie) — won't appear in public listing
    story_draft = _create_story(tok_charlie, {
        "title": "Untitled Draft — Notes on Byzantine Art",
        "content": "Work in progress. Not ready for publishing.",
        "place_name": "Istanbul",
        "latitude": 41.0082,
        "longitude": 28.9784,
    })
    # API always creates PUBLISHED+PUBLIC; demote to draft/private via direct DB update
    asyncio.run(_set_story_draft(story_draft["id"]))
    print(f"  Created: (draft) {story_draft['title']}  (id={story_draft['id'][:8]}…)")

    # ── 5. Social interactions ───────────────────────────────────────────────
    print("\n── Social interactions ──")

    # Likes
    _like(tok_bob,     story_cpl["id"])
    _like(tok_admin,   story_cpl["id"])
    _like(tok_charlie, story_cpl["id"])
    _like(tok_alice,   story_silkroad["id"])
    _like(tok_charlie, story_silkroad["id"])
    _like(tok_alice,   story_gallipoli["id"])
    _like(tok_bob,     story_hagia["id"])
    print("  Likes added")

    # Comments
    _comment(tok_bob,     story_cpl["id"],      "Incredible historical account — the detail about Mehmed II is spot on.")
    _comment(tok_charlie, story_cpl["id"],      "I visited the Theodosian Walls last year, this brought it all back!")
    _comment(tok_alice,   story_silkroad["id"], "The caravanserai network is an underrated engineering achievement.")
    _comment(tok_admin,   story_silkroad["id"], "Great research. The Seljuk road infrastructure rivals Rome's.")
    _comment(tok_charlie, story_gallipoli["id"],"ANZAC Cove is one of the most moving places I've ever visited.")
    _comment(tok_bob,     story_hagia["id"],    "The building has witnessed so many eras — breathtaking continuity.")
    print("  Comments added")

    # Bookmarks (saves)
    _save(tok_bob,     story_cpl["id"])
    _save(tok_charlie, story_cpl["id"])
    _save(tok_alice,   story_silkroad["id"])
    _save(tok_admin,   story_gallipoli["id"])
    _save(tok_alice,   story_hagia["id"])
    print("  Bookmarks added")

    # ── Done ─────────────────────────────────────────────────────────────────
    print("\n=== Seed complete ===")
    print("\nAccounts")
    print("  admin   / Admin123!   (role: admin)")
    print("  alice   / Alice123!   (role: user)")
    print("  bob     / Bobbb123!   (role: user)")
    print("  charlie / Charlie123! (role: user)")
    print("\nBrowse at http://localhost:8000/docs  or open the frontend at http://localhost:3000")


if __name__ == "__main__":
    try:
        seed()
    except RuntimeError as exc:
        print(f"\n[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
