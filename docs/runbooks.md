# Runbooks

Step-by-step guides for when things break. Written for 3 AM — no assumed context, just follow the steps.

---

## Runbook 1 — Service is down (health check failing)

**Alert:** `GET /health` returns non-200 or connection refused

**Steps:**
1. SSH into the server or open your terminal
2. Check if the process is running:
   ```bash
   lsof -i :5000
   ```
3. If nothing is running, restart the server:
   ```bash
   cd ~/team-repo
   uv run run.py
   ```
4. Verify it's back up:
   ```bash
   curl http://localhost:5000/health
   # Expected: {"status":"ok"}
   ```
5. If it crashes immediately on restart, check logs for the error:
   ```bash
   uv run run.py 2>&1 | head -50
   ```
6. Most likely causes: database is down, missing `.env` file, port 5000 already in use

---

## Runbook 2 — Database unreachable

**Alert:** `500` errors on any endpoint, logs show `OperationalError` or `could not connect to server`

**Steps:**
1. Check if PostgreSQL is running:
   ```bash
   pg_isready
   ```
2. If not running, start it:
   ```bash
   # macOS
   brew services start postgresql

   # Linux
   sudo systemctl start postgresql
   ```
3. Verify the database exists:
   ```bash
   psql -l | grep hackathon_db
   ```
4. If database doesn't exist, create it:
   ```bash
   createdb hackathon_db
   ```
5. Check your `.env` credentials match your local PostgreSQL setup:
   ```bash
   cat .env
   ```
6. Restart the Flask server after fixing:
   ```bash
   uv run run.py
   ```

---

## Runbook 3 — High error rate on API endpoints

**Alert:** Multiple 4xx or 5xx responses in logs, or Prometheus error rate metric elevated

**Steps:**
1. Check the server logs for error patterns:
   ```bash
   tail -f logs/app.log
   ```
2. Identify which endpoint is failing — look for repeated error lines
3. Common causes and fixes:

   **404 on valid endpoint:**
   - Route may not be registered — check `app/routes/__init__.py`
   - Verify the blueprint is imported and registered

   **500 on POST requests:**
   - Usually bad request body or DB constraint violation
   - Check logs for the full Python traceback
   - Test the endpoint manually with known-good data:
     ```bash
     curl -X POST http://localhost:5000/users \
       -H "Content-Type: application/json" \
       -d '{"username":"test","email":"test@test.com"}'
     ```

4. If errors are DB-related, run Runbook 2
5. If errors persist after fixes, roll back to last working commit:
   ```bash
   git log --oneline -5
   git checkout <last-good-hash>
   uv run run.py
   ```

---

## Runbook 4 — CPU or memory spike

**Alert:** `/metrics` or `/metrics/summary` showing CPU > 90% or memory > 80%

**Steps:**
1. Check current metrics:
   ```bash
   curl http://localhost:5000/metrics/summary
   ```
2. Identify what's consuming resources:
   ```bash
   top
   ```
3. If it's the Flask process, check for:
   - Infinite loops in recent code changes
   - Large unoptimized DB queries (missing pagination)
   - Too many simultaneous connections
4. Restart the server to clear the spike:
   ```bash
   # Find and kill the process
   lsof -i :5000
   kill <PID>
   uv run run.py
   ```
5. If spike returns immediately, roll back last commit and investigate offline

---

## Runbook 5 — Seed data missing or corrupt

**Alert:** Endpoints return empty arrays when they should have data, or DB queries fail

**Steps:**
1. Check if tables exist and have data:
   ```bash
   psql hackathon_db -c "SELECT COUNT(*) FROM users;"
   psql hackathon_db -c "SELECT COUNT(*) FROM urls;"
   psql hackathon_db -c "SELECT COUNT(*) FROM events;"
   ```
2. If counts are 0, re-run the seed loader:
   ```bash
   uv run load_seed.py
   ```
3. If seed loader errors, check that CSV files are present:
   ```bash
   ls -la users.csv urls.csv events.csv
   ```
4. If CSVs are missing, re-download them from the MLH platform dashboard
5. Re-run seed loader and verify counts again

---

## Golden Signals Reference

These are the four metrics every engineer watches. Check these first when something feels wrong:

| Signal | What it means | Where to check |
|---|---|---|
| Latency | How long requests take | `/metrics/summary` |
| Traffic | How many requests per second | `/metrics` |
| Errors | Rate of 4xx/5xx responses | Server logs |
| Saturation | CPU/memory usage | `/metrics/summary` |
