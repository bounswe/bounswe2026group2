# Local History Story Map

A collaborative platform for sharing and discovering local history stories tied to real geographic locations and historical dates. Users can attach photos, audio recordings, and video; explore an interactive map; search by place and date; like, comment, and bookmark stories; and record media directly in the browser.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.11, FastAPI, PostgreSQL 16 |
| Frontend | Vanilla HTML/JS, Leaflet, Nginx |
| Mobile | Capacitor + Android |
| Infrastructure | Docker Compose, GitHub Actions, Render |

## Operations

Monitoring and log aggregation setup is documented in [docs/wiki/monitoring-and-logs.md](docs/wiki/monitoring-and-logs.md).

## Quick Start

```bash
git clone https://github.com/bounswe/bounswe2026group2.git
cd bounswe2026group2
./localrun.sh
```

`localrun.sh` checks prerequisites, detects port conflicts, and starts all services. Press **Ctrl-C** to stop cleanly.

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| MinIO Console | http://localhost:9001 |

## Team

Bogazici University — CMPE354 Software Engineering Project, Group 2 (2026)
