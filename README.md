# MLH PE Hackathon — URL Shortener

A Flask app that shortens URLs, with a full monitoring stack (Prometheus, Loki, Grafana) included.

---

## Prerequisites

**1. Docker Desktop** — download from https://www.docker.com/products/docker-desktop and install it. Make sure it's open and running before you continue (look for the whale icon in your menu bar).

**2. uv** (Python package manager)

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After installing, close and reopen your terminal.

---

## Running the App

```bash
# 1. Clone and enter the project
git clone <repo-url>
cd PE-Hackathon-Template-2026

# 2. Install Python dependencies
uv sync

# 3. Start everything
docker compose up --build
```

The first run downloads Docker images — this takes a minute. Leave the terminal running.

**Verify it's working** — open a new terminal:

```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

---

## Stopping

```bash
# Ctrl+C in the Docker terminal, then:
docker compose down
```

---

## Service URLs

| Service | URL | Login |
|---|---|---|
| App | http://localhost:8000 | — |
| Grafana (logs & metrics) | http://localhost:3000 | admin / admin |
| Prometheus | http://localhost:9090 | — |

---

## Viewing Logs in Grafana

1. Open http://localhost:3000 → **Explore**
2. Select **Loki** from the dropdown
3. Query: `{service="app"}` → press **Run query**

Filter to warnings only: `{service="app"} | json | level="warning"`

---

## Viewing Metrics in Grafana

1. Open http://localhost:3000 → **Explore**
2. Select **Prometheus**
3. Example query: `rate(app_urls_created_total[1m])`

---

## Troubleshooting

**Docker won't start** — make sure Docker Desktop is open. Look for the whale icon in your menu bar.

**`uv` command not found** — close and reopen your terminal after installing. If it still fails, restart your computer.

**"Connection refused" on localhost:8000** — the app is still starting. Wait 10 seconds and try again.

**Port already in use** — run `docker compose down`, then try again.

**Code changes not showing** — rebuild with `docker compose up --build` (not just `up`).

---

## Changes by Sriky

### 1. Fixed CRLF line endings (`entrypoint.sh`, `Dockerfile`)
Windows saves files with `\r\n` line endings. Linux inside Docker can't run shell scripts with `\r` characters — it would fail with `/bin/sh^M: not found`. Converted both files to LF and added `.gitattributes` to enforce this on future commits.

### 2. Fixed PostgreSQL sequences after CSV seed
When the database is seeded from CSV files with explicit IDs (1, 2, 3...), PostgreSQL's auto-increment counter doesn't advance. So the first `POST /urls` would crash with `duplicate key violates unique constraint`. Fixed by resetting all three sequences (`users`, `urls`, `events`) at the end of `seed.py`.

### 3. Added `GET /urls/code/<short_code>` endpoint
Added a new endpoint to look up a URL record by its short code directly instead of only by numeric DB id.

```bash
curl http://localhost:8000/urls/code/2Ngd3j
```

### 4. Built a frontend UI (`app/templates/index.html`)
Added a browser-based interface at `http://localhost:8000` — paste a URL, get a short link, copy it, click it. Shows an **existing** badge if the URL was already shortened.

### 5. URL deduplication in `POST /urls`
`POST /urls` now returns the existing record (`200`) if the URL was already shortened instead of creating a duplicate. New URLs still return `201`.

### 6. Redis caching (Gold tier)
Added Redis in front of PostgreSQL for the redirect endpoint. Popular short codes are cached in memory with a 5-minute TTL — cache hits skip the DB entirely and return in under 1ms.

```
GET /<short_code>
  → Redis hit  → redirect (< 1ms, no DB)
  → Redis miss → PostgreSQL → cache → redirect
```

### 7. Nginx load balancer tuning
Replaced default nginx config with a production-tuned version:
- `least_conn` load balancing — sends requests to the least busy replica
- `worker_connections 4096` + `backlog 4096` — handles sudden connection spikes
- `worker_processes auto` — uses all CPU cores
- `keepalive 32` — reuses upstream connections

### 8. Gunicorn optimization (`entrypoint.sh`)
Bumped from 2 to 4 workers with production flags:
```sh
gunicorn --workers 4 --timeout 30 --keep-alive 2 --max-requests 1000 --max-requests-jitter 50
```
- 4 workers = 4× parallel request handling per replica
- `--max-requests 1000` restarts workers periodically to prevent memory leaks

### 9. Docker Compose scaling (3 replicas)
Increased app replicas from 2 to 3 (`deploy: replicas: 3`) giving 12 total Gunicorn worker slots behind nginx.

### 10. Autoscaler (`autoscaler.py`)
Added a Prometheus-driven autoscaler that scales app replicas up/down based on live traffic:
- Scales **up** when redirect rate > 30 req/s OR CPU > 50%
- Scales **down** after 3 consecutive low-load readings (prevents flapping)
- Min 2 replicas at rest, max 6 under load

```bash
uv run autoscaler.py
```

### 11. Load tests (Bronze / Silver / Gold / Extreme)
Added k6 load test scripts for all tiers:

| Script | Users | Requirement |
|---|---|---|
| `load_test.js` | 50 | Bronze baseline |
| `load_test_silver.js` | 200 | Silver — p95 < 3s |
| `load_test_gold.js` | 500 | Gold — p95 < 3s, errors < 5% |
| `load_test_extreme.js` | 1000 | Beyond quest — stress test |

**Results:**

| Tier | Users | p95 | Error Rate |
|---|---|---|---|
| Bronze | 50 | 16ms | 0% |
| Silver | 200 | 17.8ms | 0% |
| Gold | 500 | 64ms | 0% |
| Extreme | 1000 | 588ms | 0% |

---

## For Developers Adding Features

See the [Observability Guide](#observability-guide) below for how to add logs and metrics to your routes.

### Adding Logs

Add this at the top of every route file:

```python
import structlog
log = structlog.get_logger(__name__)
```

Then call it in your handlers:

```python
log.info("url.shortened", short_code="abc123", user_id=1)
log.warning("url.not_found", short_code="abc123")
log.error("db.write_failed", exc_info=True)
```

### Incrementing Metrics Counters

```python
from app.routes.metrics import urls_created_total, redirects_total

urls_created_total.inc()  # after a URL is successfully created
redirects_total.inc()     # after a redirect is served
```

### Registering a New Blueprint

Open `app/routes/__init__.py` and add your blueprint:

```python
def register_routes(app):
    from app.routes.metrics import metrics_bp
    app.register_blueprint(metrics_bp)

    from app.routes.urls import urls_bp  # your new blueprint
    app.register_blueprint(urls_bp)
```

---

## Error Handling

All errors are returned as JSON — the app never returns an HTML error page.

### 404 Not Found

Returned when a route or resource does not exist.

**Unmatched route** (registered in `app/__init__.py`):
```json
HTTP 404
{ "error": "not found" }
```

**Resource not found** (e.g. `GET /urls/999`):
```json
HTTP 404
{ "error": "URL not found" }
```

**Inactive short code** (redirect to a deactivated URL):
```json
HTTP 410
{ "error": "URL is inactive" }
```

### 500 Internal Server Error

Returned when an unhandled exception occurs anywhere in the app (registered in `app/__init__.py`). The exception is logged via structlog before responding.

```json
HTTP 500
{ "error": "internal server error" }
```

The full stack trace appears in the application logs (visible in Grafana → Loki, query `{service="app"} | json | level="error"`).

### 400 Bad Request

Returned by individual route handlers when required fields are missing or the request body is invalid.

```json
HTTP 400
{ "error": "original_url required" }
```

```json
HTTP 400
{ "error": "Invalid data" }
```

---

## Failure Manual

What happens when things break, and what to do about it.

### App container crashes or is killed

**What happens:** Docker detects the unexpected exit and automatically restarts the container (`restart: unless-stopped` in `docker-compose.yml`). Downtime is a few seconds.

**How to simulate:**
```bash
docker kill pe-hackathon-template-2026-app-1
```

**How to verify it recovered:**
```bash
curl http://localhost:8000/health
# → {"status": "ok"}
```

---

### Database goes down

**What happens:** The app is still running but every request that touches the DB returns:
```json
HTTP 500
{ "error": "internal server error" }
```
The full exception is logged (visible in Grafana → Loki).

**How to simulate:**
```bash
docker stop pe-hackathon-template-2026-db-1
```

**How to recover:**
```bash
docker start pe-hackathon-template-2026-db-1
```
The app reconnects automatically on the next request — no restart needed.

---

### App fails to start (DB not ready)

**What happens:** If the DB isn't healthy when the app starts, `seed.py` fails and the container exits. Docker restarts it. This repeats until the DB is ready (the `depends_on: condition: service_healthy` in `docker-compose.yml` prevents this in normal operation).

**How to identify:** Run `docker compose logs app` and look for connection refused errors.

**How to fix:** Let `docker compose up` finish fully before sending requests. The healthcheck polls every 5 seconds up to 10 times.

---

### App process dies inside the container (OOM / unhandled signal)

**What happens:** Same as a crash — Docker restarts the container automatically. Gunicorn runs with 2 workers, so if one worker dies the other continues serving requests while Docker restarts.

---

### Bad request data sent by a client

**What happens:** The app returns a clean JSON error with an appropriate status code — it does not crash.

**How to simulate:**
```bash
# Missing required field
curl -s -X POST http://localhost:8000/urls \
  -H "Content-Type: application/json" \
  -d '{}' 
# → {"error": "original_url required"}

# Non-existent resource
curl -s http://localhost:8000/urls/999999
# → {"error": "URL not found"}

# Completely unknown route
curl -s http://localhost:8000/doesnotexist
# → {"error": "not found"}
```

---

## Gold Tier — Bottleneck Report

**What was slow:** Under 500 concurrent users, the database was the bottleneck — every redirect hit PostgreSQL to look up the short code, which saturated DB connections and pushed p95 response times above 3 seconds with a ~5% error rate.

**What we fixed:** Added Redis caching in front of the database. Popular short codes are stored in memory with a 5-minute TTL, so repeated redirects skip the DB entirely — the cache hit path is a single in-memory lookup taking under 1ms vs ~20ms for a DB query.

**Result:** At 500 concurrent users, p95 dropped well under 3 seconds and error rate stayed below 5%, because only cold cache misses (first-time lookups) ever reach PostgreSQL.
