# Local History Story Map

A collaborative platform for sharing and discovering local history stories tied to real geographic locations and historical dates. Users can explore an interactive map, search by place and date, attach photos/audio/video, and interact with stories via likes, comments, and bookmarks.

- **Production:** https://localhistorymap.app/
- **Dev (Render):** https://localhistorymap-dev.onrender.com/
- **Mobile release (APK):** https://github.com/bounswe/bounswe2026group2/releases/tag/final-milestone

---

## Prerequisites

Install the following before continuing:

| Tool | Minimum version | Notes |
|------|----------------|-------|
| [Docker Desktop](https://docs.docker.com/get-docker/) / Docker Engine | 24+ | Must include **Docker Compose v2** (`docker compose`) |
| [Android Studio](https://developer.android.com/studio) | Hedgehog (2023.1) + | Required **only** for the mobile build |
| [Node.js](https://nodejs.org/) | 18+ | Required **only** for the mobile build |
| Git | any | — |

> **Verify Docker Compose v2:** run `docker compose version`. If you see `command not found`, update Docker Desktop or install the Compose plugin.

---

## 1. Clone the repository

```bash
git clone https://github.com/bounswe/bounswe2026group2.git
cd bounswe2026group2
```

---

## 2. Web Application

### 2.1 Start all services

`localrun.sh` bootstraps your `.env`, checks for port conflicts, builds images, and starts everything:

```bash
./localrun.sh
```

This brings up four services:

| Service | URL | Credentials |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | — |
| Backend API | http://localhost:8000 | — |
| Swagger UI (API docs) | http://localhost:8000/docs | — |
| MinIO object-storage console | http://localhost:9001 | `minioadmin` / `minioadmin` |

> **First run:** images are built from source, which takes a few minutes. Subsequent runs are fast.

### 2.2 Apply database migrations

In a **separate terminal** (while the services are running):

```bash
docker compose exec backend alembic upgrade head
```

This creates all tables and enums in PostgreSQL. You only need to run this once (or after pulling a migration-adding PR).

### 2.3 Populate with demo data

Seed the database with realistic stories, users, and media:

```bash
docker compose exec backend python3 seed_data.py
```

The script is idempotent — safe to run multiple times (existing users are skipped, passwords are reset to the values below).

**Demo accounts**

| Username | Password | Role |
|----------|----------|------|
| `admin` | `Admin123!` | admin |
| `alice` | `Alice123!` | user |
| `bob` | `Bobbb123!` | user |
| `charlie` | `Charlie123!` | user |

**Stories created** (all public & published unless noted)

| # | Title | Author | Location | Date | Notes |
|---|-------|--------|----------|------|-------|
| 1 | Fall of Constantinople | alice | Istanbul | year 1453 | + image attachment |
| 2 | Battle of Gallipoli | alice | Gallipoli | 1915-04-25 → 1915-12-20 | |
| 3 | The Silk Road Through Anatolia | bob | Istanbul / Ankara / Konya | year 1200–1300 | multi-location |
| 4 | A Witness to History | bob | Istanbul | year 1900–1930 | anonymous |
| 5 | Atatürk's Ankara: Birth of a Capital | admin | Ankara | 1923-10-29 | |
| 6 | Hagia Sophia Through the Ages | alice | Istanbul | 537-02-15 → 1453-05-29 | |
| 7 | Urban Legends of Istanbul | charlie | Istanbul | no date | |
| 8 | Untitled Draft — Notes on Byzantine Art | charlie | Istanbul | — | draft / private (hidden from public listing) |

**Social interactions seeded**

- Likes: stories 1, 2, 3, 6 receive likes from multiple users.
- Comments: stories 1, 2, 3, 6 receive realistic comments.
- Bookmarks: stories 1, 2, 3, 6 are bookmarked by various users.

### 2.4 Log in

1. Open http://localhost:3000
2. Click **Log in** and use any of the credentials above (e.g. `alice` / `Alice123!`).
3. Browse the map, create a story, or explore the timeline.

### 2.5 Register your own account

Click **Register** on the login page, fill in a username/email/password, and you're ready to go.

### 2.6 Stop the stack

Press **Ctrl-C** in the terminal running `localrun.sh`. All containers stop cleanly.

---

## 3. Optional: Environment Configuration

`localrun.sh` auto-creates `backend/.env` from `backend/.env.example` on first run. The defaults work out-of-the-box for local Docker Compose. To enable optional features, edit `backend/.env`:

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET_KEY` | Change from default for any shared/deployed environment |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Enables "Sign in with Google" |
| `OPENAI_API_KEY` | Enables audio transcription via Whisper API |
| `GEMINI_API_KEY` | Enables AI auto-tagging of stories |

After editing `.env`, restart the backend (no rebuild needed):

```bash
docker compose restart backend
```

---

## 4. Mobile Application (Android)

The mobile app is the same frontend wrapped in a [Capacitor](https://capacitorjs.com/) Android shell.

### 4.1 Prerequisites check

```bash
node --version   # must be 18+
npx cap --version
```

If `cap` is not found, install it: `npm install -g @capacitor/cli`

### 4.2 Install frontend dependencies

```bash
cd frontend
npm install
```

### 4.3 Build the Capacitor web bundle

```bash
npm run capacitor:sync
```

This copies the frontend files into `frontend/android/app/src/main/assets/public` and syncs Capacitor plugins.

### 4.4 Open in Android Studio

```bash
npx cap open android
```

Android Studio opens the `frontend/android` project automatically.

### 4.5 Run on a device or emulator

In Android Studio:

1. Select a connected Android device (API 24+) or start an AVD emulator.
2. Click **Run ▶** (Shift+F10).

The app connects to the production backend (`https://bounswe2026group2-backend.onrender.com`) by default. To point it at your local stack, edit `frontend/config.js` and change `API_BASE_URL` to `http://10.0.2.2:8000` (Android emulator alias for `localhost`), then re-run `npm run capacitor:sync` before building.

### 4.6 Install the pre-built APK (no build required)

Download the latest APK directly from the [final-milestone release](https://github.com/bounswe/bounswe2026group2/releases/tag/final-milestone) and sideload it:

```bash
adb install LocalHistoryMap.apk
```

Use the same demo credentials from [Section 2.3](#23-populate-with-demo-data) to log in.

---

## 5. Running Tests

```bash
# Backend — from repo root (services must be running for API/integration tests)
docker compose exec backend pytest tests/unit/
docker compose exec backend pytest tests/integration/
docker compose exec backend pytest tests/api/

# Frontend unit tests (Jest)
cd frontend && npm test

# Playwright UAT
cd frontend && npx playwright test --config=playwright.config.js

# Playwright E2E
cd frontend && npx playwright test --config=playwright.e2e.config.js
```

---

## 6. Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, SQLAlchemy (async), Alembic |
| Database | PostgreSQL 16 |
| Object Storage | MinIO (local) / Supabase S3 (prod) |
| Frontend | Vanilla HTML/JS, Leaflet, Nginx |
| Mobile | Capacitor + Android |
| Infrastructure | Docker Compose, GitHub Actions CI/CD, Render |

---

## 7. Team

Bogazici University — CMPE354 Software Engineering Project, Group 2 (2026)
