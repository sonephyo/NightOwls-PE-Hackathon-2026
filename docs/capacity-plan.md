# Capacity Plan

How many users can this service handle, and where does it break?

---

## Current Setup

- Single Flask process running on localhost
- Single PostgreSQL instance
- No caching layer
- No load balancer

---

## Baseline Performance

From the automated test results, individual endpoint response times under light load:

| Endpoint | Response Time |
|---|---|
| GET /health | ~21ms |
| GET /users | ~19ms |
| POST /users | ~15ms |
| GET /urls | ~18ms |
| POST /urls | ~20ms |
| GET /events | ~21ms |

These are single-request response times with no concurrent load.

---

## Estimated Limits

### Single server (current setup)

A single Flask development server can handle approximately **5-10 concurrent requests** before response times degrade significantly. This is because Flask's built-in server is single-threaded by default.

**Breaking point:** ~10-20 concurrent users hitting the API simultaneously will cause requests to queue and response times to spike above 1 second.

### With a production WSGI server (e.g. Gunicorn)

Running Flask behind Gunicorn with multiple workers (typically `2 * CPU cores + 1`) can handle approximately **50-100 concurrent requests** before PostgreSQL becomes the bottleneck.

### Database bottleneck

PostgreSQL on a single machine with default configuration can handle approximately **100-200 concurrent connections** before connection pool exhaustion. For this app, the ORM opens a connection per request — heavy load will hit this limit.

---

## Where It Breaks

1. **Flask dev server** — not designed for production load, queues requests
2. **No connection pooling** — each request opens a new DB connection
3. **No caching** — every GET /urls or GET /users hits the database directly
4. **Single instance** — no horizontal scaling, one point of failure

---

## How to Scale (next steps)

| Problem | Solution |
|---|---|
| Flask dev server limit | Switch to Gunicorn with multiple workers |
| No connection pooling | Add pgbouncer or configure Peewee's connection pool |
| Database read bottleneck | Add Redis caching for frequently read endpoints |
| Single instance | Docker Compose + Nginx load balancer (see Scalability track) |

---

## Load Test Results

Test environment: MLH PE Hackathon automated test suite
Result: **27/29 tests passing** with response times averaging 15-25ms per endpoint under sequential (non-concurrent) load.

For concurrent load testing results, see the Scalability track documentation.
