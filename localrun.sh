#!/bin/bash
set -e

# ── Colors ────────────────────────────────────────────────────────────────────
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

info()    { echo -e "${CYAN}[localrun]${NC} $*"; }
success() { echo -e "${GREEN}[localrun]${NC} $*"; }
warn()    { echo -e "${YELLOW}[localrun] WARNING:${NC} $*"; }
error()   { echo -e "${RED}[localrun] ERROR:${NC} $*" >&2; }

# ── Prereqs ───────────────────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  error "Docker not found. Install Docker Desktop or Docker Engine first."
  exit 1
fi

if ! docker compose version &>/dev/null 2>&1; then
  error "Docker Compose (v2) not found. Run: docker plugin install compose"
  exit 1
fi

if ! docker info &>/dev/null 2>&1; then
  error "Docker daemon is not running. Start Docker and retry."
  exit 1
fi

# ── Port conflict detection ───────────────────────────────────────────────────
declare -A PORT_NAMES=(
  [5432]="PostgreSQL (db)"
  [8000]="Backend (FastAPI)"
  [9000]="MinIO S3 API"
  [9001]="MinIO Web UI"
  [3000]="Frontend (Nginx)"
)

PIDS_TO_KILL=()
PORTS_TO_FREE=()
CONTAINERS_TO_STOP=()

# Check Docker containers holding ports (Docker network driver binds ports,
# so lsof won't see them — must query Docker directly)
for port in 5432 8000 9000 9001 3000; do
  cid=$(docker ps --filter "publish=$port" --format "{{.ID}}" 2>/dev/null | head -1 || true)
  if [[ -n "$cid" ]]; then
    cname=$(docker ps --filter "publish=$port" --format "{{.Names}}" 2>/dev/null | head -1)
    warn "Port $port (${PORT_NAMES[$port]}) is held by Docker container $cname ($cid)"
    CONTAINERS_TO_STOP+=("$cid")
    PORTS_TO_FREE+=("$port")
  else
    # Fallback: check user-space processes (non-Docker)
    pid=$(lsof -ti tcp:"$port" 2>/dev/null | head -1 || true)
    if [[ -n "$pid" ]]; then
      proc=$(ps -p "$pid" -o comm= 2>/dev/null || echo "unknown")
      warn "Port $port (${PORT_NAMES[$port]}) is occupied by PID $pid ($proc)"
      PIDS_TO_KILL+=("$pid")
      PORTS_TO_FREE+=("$port")
    fi
  fi
done

if [[ ${#CONTAINERS_TO_STOP[@]} -gt 0 || ${#PIDS_TO_KILL[@]} -gt 0 ]]; then
  echo ""
  echo -e "${BOLD}The following ports are in use:${NC}"
  for port in "${PORTS_TO_FREE[@]}"; do
    cid=$(docker ps --filter "publish=$port" --format "{{.ID}}" 2>/dev/null | head -1 || true)
    if [[ -n "$cid" ]]; then
      cname=$(docker ps --filter "publish=$port" --format "{{.Names}}" 2>/dev/null | head -1)
      echo -e "  • Port $port — Docker container $cname"
    else
      pid=$(lsof -ti tcp:"$port" 2>/dev/null | head -1 || true)
      [[ -n "$pid" ]] && echo -e "  • Port $port — PID $pid"
    fi
  done
  echo ""
  read -rp "Stop/kill these and free the ports? [y/N] " answer
  if [[ "$answer" =~ ^[Yy]$ ]]; then
    for cid in "${CONTAINERS_TO_STOP[@]}"; do
      docker stop "$cid" &>/dev/null && info "Stopped container $cid" || warn "Could not stop container $cid"
    done
    for pid in "${PIDS_TO_KILL[@]}"; do
      kill -9 "$pid" 2>/dev/null && info "Killed PID $pid" || warn "Could not kill PID $pid (may need sudo)"
    done
    sleep 1
  else
    error "Aborting — ports still in use. Free them manually and retry."
    exit 1
  fi
fi

# ── .env bootstrap ────────────────────────────────────────────────────────────
ENV_FILE="./backend/.env"
ENV_EXAMPLE="./backend/.env.example"

if [[ ! -f "$ENV_FILE" ]]; then
  if [[ -f "$ENV_EXAMPLE" ]]; then
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    warn ".env not found — copied from .env.example with default Docker Compose settings."
    warn "Edit backend/.env if you need custom credentials (JWT_SECRET_KEY, OAuth keys, etc.)"
  else
    warn ".env not found and no .env.example to copy from."
    warn "Backend will likely fail to connect to DB/MinIO. Create backend/.env before running."
    warn "Continuing build anyway — container will start but connections may fail."
  fi
else
  info "Found backend/.env"
fi

# ── Build & start ─────────────────────────────────────────────────────────────
echo ""
info "Starting all services (this builds images if needed)..."
echo ""

# Trap Ctrl-C to bring everything down cleanly
trap 'echo ""; info "Shutting down..."; docker compose down; exit 0' INT TERM

docker compose up --build "$@"
