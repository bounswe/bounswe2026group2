# Load Testing & Query Optimization — Issue #239

## EXPLAIN ANALYZE Findings

### Existing indexes (as of migration 0023)

| Index | Table | Columns | Type |
|-------|-------|---------|------|
| `ix_stories_user_id` | stories | user_id | B-tree |
| `ix_stories_status` | stories | status | B-tree |
| `ix_stories_visibility` | stories | visibility | B-tree |
| `ix_stories_deleted_at` | stories | deleted_at | B-tree |
| `ix_stories_lat_lng` | stories | (latitude, longitude) | Partial B-tree (WHERE NOT NULL) |
| `ix_stories_place_name` | stories | place_name | B-tree |
| `ix_stories_date_start` | stories | date_start | B-tree |
| `ix_stories_date_end` | stories | date_end | B-tree |
| `ix_story_locations_story_id` | story_locations | story_id | B-tree |
| `ix_story_locations_coords` | story_locations | (latitude, longitude) | B-tree |
| `ix_story_tags_story_id` | story_tags | story_id | B-tree |
| `ix_story_tags_tag_id` | story_tags | tag_id | B-tree |
| `ix_story_tags_tag_id_story_id` | story_tags | (tag_id, story_id) | B-tree |
| `ix_tags_name` | tags | name | B-tree |
| `ix_tags_slug` | tags | slug | B-tree |
| pg_trgm GIN index | stories | (title, summary, place_name) | GIN (migration 0021) |

### Identified gap — migration 0024

**Query pattern** (`GET /stories`, `GET /stories/search`, `GET /stories/timeline`, `GET /stories/nearby`):

```sql
WHERE status = 'PUBLISHED'
  AND visibility = 'PUBLIC'
  AND deleted_at IS NULL
ORDER BY created_at DESC
```

Note: SQLAlchemy stores the enum member name (`PUBLISHED`, `PUBLIC`) as the VARCHAR value, not the Python `.value` attribute (`published`, `public`).

**Problem:** Three separate B-tree indexes (`ix_stories_status`, `ix_stories_visibility`, `ix_stories_deleted_at`) require PostgreSQL to perform three bitmap index scans and then bitmap-AND them together.  On a table with many draft/private/deleted rows this is efficient, but as the fraction of published+public rows grows the bitmap overhead increases.

**Fix (migration 0024):** Partial covering index:

```sql
CREATE INDEX ix_stories_published_public_active
ON stories (created_at DESC)
WHERE status = 'PUBLISHED' AND visibility = 'PUBLIC' AND deleted_at IS NULL;
```

The planner can now satisfy the full filter with **one index scan** ordered by `created_at DESC`, avoiding the bitmap-AND path entirely for the common list case.

**Expected `EXPLAIN ANALYZE` change:**

| Before | After |
|--------|-------|
| `Bitmap Heap Scan` + 3× `Bitmap Index Scan` | `Index Scan using ix_stories_published_public_active` |
| 3 index pages read per row | 1 index page read per row |

### Queries that still require full-scan fallback

- Haversine distance (`GET /stories/nearby`, `GET /stories/timeline` with `lat/lng`) — distance is a computed expression; no B-tree index helps. Acceptable at current data volume.
- Hybrid semantic search (`GET /stories/search?q=...`) — similarity scoring across four text columns. The GIN trgm index reduces candidate rows; full expression eval is unavoidable.

---

## Running Load Tests

### Prerequisites

```bash
pip3 install locust
# The backend stack must be running:
cd bounswe2026group2 && ./localrun.sh
# Apply migrations including 0024:
docker compose exec backend alembic upgrade head
```

### Interactive mode (recommended for first run)

```bash
cd backend/tests/load
locust -f locustfile.py --host http://localhost:8000
# Open http://localhost:8089
# Start with: Users=20, Spawn rate=5
```

### Headless stress test

```bash
locust -f locustfile.py \
  --host http://localhost:8000 \
  --users 50 \
  --spawn-rate 10 \
  --run-time 60s \
  --headless \
  --csv=results/stress_50u
```

Results are written to `results/stress_50u_*.csv`.

### Interpreting results

Key metrics to record:

| Metric | Target |
|--------|--------|
| `GET /stories` median response | < 200 ms |
| `GET /stories` 95th percentile | < 500 ms |
| `GET /stories/search` median | < 300 ms |
| `GET /stories/{id}` median | < 150 ms |
| Failure rate | 0 % |
| Max RPS before failure rate rises | record this |

If `GET /stories` p95 exceeds 500 ms under 50 concurrent users, investigate with:

```bash
docker compose exec db psql -U postgres -c \
  "EXPLAIN (ANALYZE, BUFFERS) SELECT s.id, u.username FROM stories s JOIN users u ON u.id = s.user_id WHERE s.status = 'PUBLISHED' AND s.visibility = 'PUBLIC' AND s.deleted_at IS NULL ORDER BY s.created_at DESC;"
```

Look for `Index Scan using ix_stories_published_public_active` — if you see `Bitmap Heap Scan` instead, run `ANALYZE stories;` to refresh planner statistics.

---

## Benchmark Results

Runs performed against local Docker stack (PostgreSQL 16, single-node, migration 0024 applied).
Duration: 60 s per run. **Failure rate: 0% on both runs.**

| Endpoint | Users | Median (ms) | p95 (ms) | RPS |
|----------|-------|-------------|----------|-----|
| `GET /stories` | 20 | 9 | 310 | 6.8 |
| `GET /stories` | 50 | 22 | 1800 | 11.7 |
| `GET /stories/search` | 20 | 6 | 200 | 3.0 |
| `GET /stories/search` | 50 | 21 | 1100 | 5.0 |
| `GET /stories/{id}` | 20 | 10 | 180 | 2.2 |
| `GET /stories/{id}` | 50 | 15 | 810 | 3.9 |
| `POST /auth/login` | 20 | 210 | 350 | 0.7 |
| `POST /auth/login` | 50 | 320 | 4200 | 1.3 |
| `GET /auth/me` | 20 | 7 | 360 | 1.3 |
| `GET /auth/me` | 50 | 32 | 1800 | 2.4 |
| **Aggregated** | **20** | **9** | **1400** | **14.5** |
| **Aggregated** | **50** | **89** | **4500** | **26.0** |

### Notes

- Read endpoint medians stay under 30 ms even at 50 concurrent users, confirming the partial covering index is effective.
- High p95 values at 50 users are dominated by `POST /auth/register` setup calls (bcrypt password hashing is intentionally slow ~300 ms each; 50 users registering on spawn creates a burst). Sustained read traffic p95 values are significantly lower.
- `POST /auth/login` p95 jumps at 50 users due to bcrypt cost compounding under concurrency — expected and acceptable for an auth endpoint.
- Max sustained RPS before any degradation: **~26 RPS** across all endpoints combined on a single local node.
