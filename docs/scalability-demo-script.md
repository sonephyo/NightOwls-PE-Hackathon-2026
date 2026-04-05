# Scalability Quest — Video Demo Script

## Overview (30 seconds)

> "Our system is a URL shortener built with Flask, Gunicorn, PostgreSQL, Redis, and Nginx.
> We designed it from the ground up to handle rising traffic — starting with basic load testing
> tooling and working up to a full multi-instance, cached, load-balanced production setup."

---

## BRONZE — Load Testing Tooling + 50 Concurrent Users

### What we did
We chose **k6** as our load testing framework. k6 is written in Go, runs test scripts in JavaScript,
and produces detailed performance summaries including p50, p95, p99 latency and error rates — exactly
what we need to prove scalability.

We wrote `load_test.js` — a bronze-tier script that:
- Spins up **50 virtual users (VUs)** simultaneously
- Runs for **1 full minute**
- Hits the redirect endpoint (`GET /<short_code>`) — the most traffic-critical route
- Sets a threshold: p95 latency must be under 500ms, error rate under 5%

### Why we did it this way
The redirect endpoint is the hot path. In a URL shortener, every click goes through it.
If anything is going to break under load, it breaks here first. We also intentionally
do NOT follow redirects (`redirects: 0`) so we measure our server response time, not
the destination site's response time.

### Problems we faced
- **Short codes not in the database**: Our first test run returned all 404s because the
  test script used hardcoded short codes that didn't exist in the seeded database.
  Fix: we matched the short codes in the script to what `seed.py` actually inserts.
- **BASE_URL hardcoded to localhost**: The script originally pointed to `localhost:8000`
  which only works locally. Fix: updated to use `__ENV.TARGET` so we can pass the live
  server URL via command line without editing code.

### How to demo — show this on screen
```bash
# Show the test file
cat load_test.js

# Run against the live server
k6 run load_test.js

# Point at what matters in the output:
# ✓ redirect or not found
# ✓ response time < 500ms
# http_req_duration p(95)=...
# http_req_failed rate=0.00%
```

**Say:** _"You can see 50 virtual users hitting the server simultaneously for 60 seconds.
All checks pass. p95 latency is well under our 500ms threshold and error rate is 0%."_

---

## SILVER — 200 Users + Multiple Instances + Load Balancer

### What we did

**1. Scale to 200 concurrent users** — `load_test_silver.js` uses 200 VUs for 2 minutes
with a stricter threshold (p95 < 3 seconds, error rate < 5%).

**2. Multiple app instances** — `docker-compose.yml` runs **3 app replicas** using Docker
Compose's deploy config:
```yaml
deploy:
  replicas: 3
```
Each replica is an independent Gunicorn process with 4 workers × 4 threads = 16 threads per replica,
giving us **48 concurrent threads** total across the cluster.

**3. Load balancer** — Nginx acts as the load balancer using the `least_conn` algorithm,
which routes each new request to whichever app instance has the fewest active connections
(smarter than round-robin under variable request durations):
```nginx
upstream app_servers {
    least_conn;
    server app:8000 max_fails=3 fail_timeout=30s;
    keepalive 64;
}
```

### Why we did it this way
At 200 concurrent users with ~10ms average response time, a single Gunicorn instance
would queue requests. By running 3 replicas behind Nginx, we multiply our throughput
capacity by 3x with zero application code changes — just a config change.

`least_conn` beats round-robin here because redirect responses are fast (cached) but
some requests (DB writes, health checks) take longer. `least_conn` prevents one slow
instance from getting piled on.

### Problems we faced
- **Nginx crash-looping in CI**: When we added nginx to our CI pipeline, it crashed because
  SSL certificates don't exist in the CI environment and `alertmanager` wasn't started.
  This blocked the health check and failed every docker CI job.
  Fix: wrote a `docker-compose.ci.yml` override that skips nginx entirely in CI,
  exposing the app directly on port 8000 for health checks.
- **Port mismatch killing the domain**: We had nginx mapped to port `8000:80` in docker-compose,
  meaning `night-owls.duckdns.org` (which defaults to port 80) refused to connect.
  Fix: changed to `80:80` so the domain resolves correctly.

### How to demo — show this on screen
```bash
# Show docker-compose.yml — point to replicas: 3
cat docker-compose.yml | grep -A3 "deploy:"

# Show nginx.conf — point to least_conn upstream
cat nginx/nginx.conf | grep -A5 "upstream"

# Run 200 VU test
k6 run load_test_silver.js

# Point at output:
# http_req_duration p(95)=... (must be under 3000ms)
# http_req_failed rate=0.00%
```

**Say:** _"Three app instances are running behind Nginx's least_conn load balancer.
200 users hit the system for 2 minutes. p95 stays under 3 seconds and error rate is 0%.
The load is distributed evenly — no single instance gets overwhelmed."_

---

## GOLD — 500 Users + Redis Caching + Bottleneck Analysis

### What we did

**1. Tsunami-level test** — `load_test_gold.js` ramps up to **500 VUs** over 20 seconds,
holds for 2 minutes, then ramps back down. This simulates a real traffic spike.

**2. Redis caching** — The redirect hot path checks Redis before hitting PostgreSQL:
```
GET /<short_code>
  → Redis HIT  → return cached URL (2–5ms, no DB query)
  → Redis MISS → query PostgreSQL → cache result for 60s → return URL
```

Implemented in `app/routes/urls.py` with:
- `_cache_get(short_code)` — fetch from Redis
- `_cache_set(short_code, url)` — store with 60s TTL
- `_cache_delete(short_code)` — invalidate on deactivate/delete

At 500 VUs rotating through 14 short codes, the cache hit rate is **>95%** — meaning
the database sees less than 5% of the traffic it would see without caching.

**3. Bottleneck analysis** — documented in `reports/bottleneck-analysis.md`, covering:
- DB connection pool limit (max 20 connections → pool exhaustion above 500 VUs)
- Gunicorn thread saturation point (~1000+ VUs)
- Async click queue design (writes never block HTTP response)
- Redis as the primary scalability lever

### Why we did it this way
Without Redis, every redirect hits PostgreSQL. PostgreSQL can handle maybe 200–500 simple
queries per second on this droplet. At 500 VUs with ~1s think time, that's 500 req/s.
Without caching, we'd exhaust the DB immediately.

With Redis caching, 95%+ of requests never touch the DB. Redis handles hundreds of thousands
of operations per second. This is the single biggest scalability win in the system.

The async click queue is the second key decision — click recording (analytics) should never
slow down a redirect. We enqueue the click event in memory and a background thread batch-inserts
every 500ms. The user gets their redirect immediately.

### Problems we faced
- **Docker socket permissions**: Our CI deploy user (`deploy`) couldn't run `docker compose`
  because it wasn't in the docker group. We tried `sudo`, but sudo requires an interactive
  terminal in SSH sessions. Fix: `chmod 666 /var/run/docker.sock` on the server gives the
  deploy user access without sudo.
- **git pull blocked by local changes**: The server had a locally-modified `nginx/nginx.conf`
  that blocked `git pull`. Every deploy failed with "your local changes would be overwritten."
  Fix: added `git checkout -- .` before `git pull` in the deploy script to always start from
  a clean state.
- **Redis URL format change**: Mid-hackathon, MLH provided a `REDIS_URL` environment variable
  (`redis://localhost:6379/0`) instead of separate host/port vars. We updated both connection
  points to use `Redis.from_url(REDIS_URL)` with a fallback to `REDIS_HOST`/`REDIS_PORT` for
  local dev compatibility.

### How to demo — show this on screen
```bash
# Show Redis cache implementation
cat app/routes/urls.py | grep -A10 "_get_redis\|_cache_get\|_cache_set"

# Show bottleneck analysis report
cat reports/bottleneck-analysis.md

# Run gold test (500 VUs)
k6 run load_test_gold.js

# Point at output:
# stages: ramp 0→500, hold 500, ramp 500→0
# http_req_duration p(95)=... (under 3000ms)
# http_req_failed rate=0.00% (under 5%)
```

**Say:** _"500 users ramp up over 20 seconds. Redis is absorbing 95%+ of the redirect
traffic — the database barely moves. p95 stays well under 3 seconds and error rate is 0%.
The bottleneck analysis in our reports folder documents exactly where the limits are and
what we'd do to push further."_

---

## Closing Summary (20 seconds)

> "To summarize our scalability story:
>
> **Bronze** — k6 load testing, 50 users, baseline metrics documented.
>
> **Silver** — 3 app replicas, Nginx least_conn load balancer, 200 users with p95 under 3 seconds.
>
> **Gold** — Redis caching eliminates 95%+ of DB load, 500-user tsunami test passes,
> full bottleneck analysis documented in the repo.
>
> The system is deployed live at night-owls.duckdns.org and all the code,
> config, and reports are in the GitHub repo."

---

## Quick Reference — GitHub Links for Submission Form

| Field | Link |
|---|---|
| k6 tooling configured | `https://github.com/sonephyo/NightOwls-PE-Hackathon-2026/blob/main/load_test.js` |
| 50 VU test | `https://github.com/sonephyo/NightOwls-PE-Hackathon-2026/blob/main/load_test.js` |
| Multiple app instances | `https://github.com/sonephyo/NightOwls-PE-Hackathon-2026/blob/main/docker-compose.yml` |
| Load balancer config | `https://github.com/sonephyo/NightOwls-PE-Hackathon-2026/blob/main/nginx/nginx.conf` |
| Redis caching | `https://github.com/sonephyo/NightOwls-PE-Hackathon-2026/blob/main/app/routes/urls.py` |
| Bottleneck analysis | `https://github.com/sonephyo/NightOwls-PE-Hackathon-2026/blob/main/reports/bottleneck-analysis.md` |
