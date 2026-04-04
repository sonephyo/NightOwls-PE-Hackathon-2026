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
