---
sidebar_position: 2
title: Runbooks
---

# Runbooks

> At 3 AM you are not functioning. This document is.

## Quick Links
| Tool | URL |
|------|-----|
| Grafana — Metrics Dashboard | http://localhost:3000/d/app-overview |
| Grafana — Logs Dashboard | http://localhost:3000/d/logs-overview |
| Prometheus Alerts | http://localhost:9090/alerts |
| Alertmanager | http://localhost:9093 |

Two alerts are configured in Prometheus. This document tells you exactly what to do when each fires.

---

## Alert: `FlaskAppDown`

**Condition:** Prometheus cannot scrape `app:8000/metrics` for 1 minute.  
**Severity:** Critical  
**What it means:** The app container has crashed, hung, or lost network connectivity.

### 1. Confirm the alert

Open AlertManager at `http://localhost:9093` and verify `FlaskAppDown` is active.  
Check Prometheus at `http://localhost:9090/targets` — the `flask-app` job should show state `DOWN`.

### 2. Check container state

```bash
docker ps -a --filter name=app
```

| State | Next step |
|---|---|
| `Up` | App is running but `/metrics` is unreachable → go to step 4 |
| `Exited` | Container crashed → go to step 3 |
| Not listed | Container was killed or never started → go to step 3 |

### 3. Restart the app container

```bash
docker compose restart app
```

Wait 10–15 seconds (seed script runs on startup), then verify:

```bash
curl http://localhost:8000/health
# Expected: {"status": "ok"}
```

If the container exits again immediately, read the crash logs:

```bash
docker compose logs app --tail=50
```

Common causes:
- **Database not ready:** `db` container is unhealthy. Run `docker compose restart db`, wait for `healthy`, then restart `app`.
- **Missing env var:** `DATABASE_HOST` or `DATABASE_PASSWORD` not set. Check `.env` file exists and is populated.
- **Port conflict:** Something else is bound to 8000. Run `lsof -i :8000` and kill the conflicting process.

### 4. App is running but unreachable

If `docker ps` shows the container is `Up` but the alert is still firing:

```bash
# Confirm the route is accessible
curl -v http://localhost:8000/metrics

# Check if gunicorn workers are alive inside the container
docker compose exec app ps aux | grep gunicorn
```

If no gunicorn workers are listed, the process died silently. Restart:

```bash
docker compose restart app
```

If workers are running but `/metrics` times out, check for a stuck request consuming all 2 workers (e.g., a long-running `/stress` or bulk upload). Restart to clear.

### 5. Verify recovery

Alert auto-resolves in Prometheus within 1 minute of `/metrics` becoming reachable again.  
PagerDuty will receive a resolve event automatically.

---

## Alert: `HighErrorRate`

**Condition:** HTTP 5xx responses exceed 10% of total traffic for 1 minute (requires at least 1 req/2m to suppress noise).  
**Severity:** Critical  
**What it means:** A significant portion of requests are hitting unhandled server errors.

### 1. Confirm the alert

In Prometheus, run this query to see the current error rate:

```
sum(rate(http_requests_total{http_status=~"5.."}[2m])) 
/ 
sum(rate(http_requests_total[2m]))
```

A value above `0.10` confirms the alert condition.

### 2. Identify which endpoint is failing

```
sum by (endpoint) (rate(http_requests_total{http_status=~"5.."}[2m]))
```

This shows you which route is throwing errors. Cross-reference with Loki:

In Grafana (`http://localhost:3000`), query:

```
{service_name="nightowls-app-1"} | json | level="error"
```

Look for `event` field values — the structured logger names the operation (e.g., `unhandled_exception`, `db.connection_error`).

### 3. Common causes and fixes

**Database connection failure**

Logs show: `OperationalError`, `connection refused`, or `too many connections`

```bash
# Check DB health
docker compose exec db pg_isready -U postgres

# If unhealthy, restart DB
docker compose restart db

# Then restart app to re-establish connections
docker compose restart app
```

Peewee opens one connection per request and closes it in `teardown_appcontext`. With 2 gunicorn workers under high load, connections can exhaust. If this recurs, reduce load or add a connection pooler.

**Unhandled exception in a route**

Logs show a Python traceback under `event="unhandled_exception"`.

The global 500 handler in `app/__init__.py` catches all unhandled exceptions and returns:
```json
{"error": "internal server error"}
```

Identify the failing route from the Loki log, then check the specific route handler in `app/routes/`. The most common causes are:
- Malformed request body hitting a `.get()` without a default
- A database model constraint violation not caught by the route
- A `None` dereference on a missing FK record

Apply a targeted fix to the route and redeploy:

```bash
docker compose up --build -d app
```

**Bulk upload CSV causing partial failures**

`POST /users/bulk` and `POST /urls/bulk` wrap inserts in `db.atomic()`. If a row fails validation mid-batch, the entire batch rolls back and returns 500. Check logs for the failing row:

```
{service_name="nightowls-app-1"} | json | event="bulk_insert_error"
```

Fix the CSV (bad row IDs, missing required fields, duplicate emails) and retry the request.

**`/stress` endpoint triggered**

`GET /stress` burns CPU for ~3 seconds. If called repeatedly, it can cause gunicorn workers to queue up and timeout, producing 500s. Check:

```
{service_name="nightowls-app-1"} | json | event="stress_complete"
```

If this is the cause, the errors will self-resolve once the load stops. No action needed unless this is being called maliciously.

### 4. Verify recovery

In Prometheus, the `HighErrorRate` alert will auto-resolve once the 5xx rate drops below 10% for 1 sustained minute. Check:

```
sum(rate(http_requests_total{http_status=~"5.."}[2m])) / sum(rate(http_requests_total[2m]))
```

Should return a value below `0.10` or `no data` (if traffic has stopped).

---

---

## Sherlock Mode: Root Cause Diagnosis Demo

**Scenario:** Error Rate stat turns red. Users report slowness and 500 errors.

**Step 1 — Metrics dashboard top row**
- App Status: green → app is up, not crashed
- Error Rate %: red → errors are happening
- Latency p95: elevated → requests are slow

**Step 2 — Traffic & Errors row**
- Traffic panel: requests still flowing to endpoints → app is responding, just badly
- Error Rate timeseries: spike started at a specific timestamp — note it

**Step 3 — Saturation row**
- CPU timeseries: repeated spikes every ~5 seconds correlating exactly with the error spike
- Latency spikes match CPU spikes → CPU contention is causing timeouts

**Step 4 — Switch to Logs dashboard**
- Log Volume chart: error-level lines spike at the same time as the CPU
- Errors & Warnings panel: `"event": "simulated_error", "endpoint": "/test-error"` flood starting at the noted timestamp
- All Logs panel: high volume of requests to `/test-error` and `/stress`

**Root cause:**
> A client began hammering `/stress` (CPU spike) and `/test-error` simultaneously at the noted time. The CPU saturation caused all other requests to slow down and timeout, producing the error spike. The log stream confirms the exact start time and endpoints involved.

**Resolution:** Rate-limit or remove `/stress` and `/test-error` from production builds.

---

## General Commands

```bash
# View live app logs
docker compose logs -f app

# Restart everything
docker compose down && docker compose up -d

# Full reset (clears database)
docker compose down -v && docker compose up --build -d

# Check all container health
docker compose ps

# Hit health check manually
curl http://localhost:8000/health
```
