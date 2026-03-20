# Local History Story Map

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

## Setup

1. Clone the repository
   ```bash
   git clone https://github.com/bounswe/bounswe2026group2.git
   cd bounswe2026group2
   ```

## Running Locally

```bash
./localrun.sh
```

This builds and starts all services via Docker Compose.

| Service  | URL                   |
|----------|-----------------------|
| Backend  | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |

## Stopping

```bash
docker compose down
```
