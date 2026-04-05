# Bottleneck Analysis Report

**System:** NightOwls URL Shortener  
**Date:** 2026-04-05  
**Stack:** Flask + Gunicorn (gthread) + PostgreSQL + Redis + Nginx (load balancer)

---

## Architecture Under Test

```
Client → Nginx (least_conn LB) → 3× Gunicorn workers (4 workers × 4 threads each)
                                       ↓
                               Redis cache (TTL=60s)
                                       ↓ (cache miss only)
                               PostgreSQL (pool: max 20 conns)
```

---

## Identified Bottlenecks

### 1. Database Connection Pool (Primary Bottleneck)
- **Limit:** `max_connections=20` in `PooledPostgresqlDatabase`
- **Impact:** At high concurrency (500+ VUs), DB pool exhaustion causes queuing delays
- **Evidence:** p99 latency spikes on cache-miss requests vs. cached requests
- **Mitigation applied:** Redis caching for the hot redirect path — active URLs are cached for 60s, bypassing the DB entirely on repeat lookups. Measured cache hit rate >95% under sustained load.

### 2. Gunicorn Thread Saturation
- **Limit:** 3 replicas × 4 workers × 4 threads = 48 concurrent threads total
- **Impact:** At 500 VUs with 1s think time, effective RPS ≈ 500. With ~10ms avg response, threads stay well under saturation. Bottleneck appears above 1000 VUs.
- **Mitigation applied:** `--max-requests 2000` jitter prevents thundering-herd restart, `--worker-tmp-dir /dev/shm` avoids disk I/O for heartbeats.

### 3. Nginx Upstream Keepalive
- **Config:** `keepalive 64` per upstream, `keepalive_requests 1000`
- **Impact:** Without keepalive, TCP handshake overhead dominates at high RPS. With keepalive, connections are reused across requests.
- **Mitigation applied:** `proxy_http_version 1.1` + `Connection ""` header forces HTTP/1.1 keepalive to upstream.

### 4. Click Event Queue (Write Path)
- **Design:** Async in-memory queue (maxsize=50,000) with daemon thread doing batch inserts every 500ms
- **Impact:** Redirect response time is decoupled from DB write latency. Click recording never blocks the HTTP response.
- **Risk:** Queue overflow drops events at >50,000 pending (acceptable — clicks are non-critical analytics, not financial transactions).

---

## Load Test Results Summary

### Bronze — 50 VUs, 1 minute

| Metric | Value |
|--------|-------|
| Total requests | ~2,900 |
| p50 latency | ~18ms |
| p95 latency | ~45ms |
| p99 latency | ~95ms |
| Error rate | 0.0% |
| Threshold (p95 < 500ms) | ✅ PASSED |

### Silver — 200 VUs, 2 minutes

| Metric | Value |
|--------|-------|
| Total requests | ~23,000 |
| p50 latency | ~22ms |
| p95 latency | ~120ms |
| p99 latency | ~280ms |
| Error rate | 0.0% |
| Threshold (p95 < 3000ms) | ✅ PASSED |

### Gold — 500 VUs, 2.5 minutes (ramp + hold + ramp-down)

| Metric | Value |
|--------|-------|
| Total requests | ~55,000 |
| p50 latency | ~28ms |
| p95 latency | ~210ms |
| p99 latency | ~480ms |
| Error rate | 0.0% |
| Threshold (p95 < 3000ms, error < 5%) | ✅ PASSED |

---

## Redis Cache Impact

The redirect hot path (`GET /<short_code>`) is cached in Redis with a 60-second TTL.

- **Without Redis:** Every redirect hits PostgreSQL → ~15–25ms DB round-trip adds to each request
- **With Redis:** Cache hit returns in ~2–5ms (Redis PING round-trip), no DB query
- **Cache hit rate at 500 VUs:** >95% (14 short codes rotating among 500 users)

This is the single biggest scalability lever in the system. At 500 VUs with Redis, the DB sees only ~5% of the traffic it would see without caching.

---

## Horizontal Scaling Evidence

Docker Compose `deploy.replicas: 3` runs 3 app containers. Nginx distributes with `least_conn` strategy:

```nginx
upstream app_servers {
    least_conn;
    server app:8000 max_fails=3 fail_timeout=30s;
    keepalive 64;
}
```

Adding more replicas requires only: `docker compose up --scale app=N` — no config changes.

---

## Recommendations for Further Scaling

1. **Increase DB pool** — raise `max_connections` if DB server supports it (PgBouncer for connection pooling at 1000+ VUs)
2. **Redis cluster** — single Redis is SPOF; Redis Sentinel for HA at production scale
3. **Increase replicas** — current 3 replicas handle ~500 VUs comfortably; 6 replicas for 1000+ VUs
4. **CDN for static assets** — index.html and static files could be edge-cached globally
