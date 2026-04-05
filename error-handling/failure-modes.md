# Failure Modes

What breaks, what the app does, and how to recover.

---

## 1. Database Unreachable

**What happens:** All endpoints that touch the DB return 500. The `/health` endpoint still returns 200 (it does not check DB connectivity).

**Detection:** 500 responses on /urls, /users, /events. Check logs for `OperationalError` or `connection refused`.

**Recovery:**
```bash
# Check if postgres is running
docker compose ps db

# Restart it
docker compose restart db

# Verify
docker compose exec db pg_isready -U postgres
```

---

## 2. Redis Unreachable

**What happens:** The app degrades gracefully — Redis cache is skipped, all requests fall through to the database. No data loss, slightly higher DB load.

**Detection:** Redirect latency increases slightly. Check logs for Redis connection errors.

**Recovery:**
```bash
docker compose restart redis
```

The app reconnects automatically on the next request.

---

## 3. Bad Request Body

**What happens:** The app validates all input at the route level before touching the DB. Bad input is rejected immediately with 400 and a descriptive error message.

**Examples:**
- `POST /urls` with `user_id: "abc"` → `{"error": "user_id must be an integer"}`
- `POST /events` with `details: [1,2,3]` → `{"error": "details must be an object"}`
- `POST /users` with unknown field → `{"error": "Invalid data"}`

No partial writes occur — validation happens before any DB operation.

---

## 4. Inactive or Deleted URL Redirect

**What happens:** `GET /<short_code>` returns 404. No redirect occurs. No click event is created. No metric is incremented.

**Why:** Inactive/deleted URLs leave no footprint — 404 reveals nothing about whether the URL ever existed.

---

## 5. Duplicate Short Code on Create

**What happens:** If the requested `short_code` already exists, the app automatically generates a new unique one and uses it instead of failing. The response is still 201.

**If no short code provided:** A unique 6-character alphanumeric code is auto-generated.

---

## 6. Duplicate Original URL on Create

**What happens:** If the same `original_url` is submitted again, the existing record is returned with status 200. No duplicate is created.

---

## 7. Unhandled Exception

**What happens:** Flask's 500 error handler catches it, logs the full traceback server-side, and returns:
```json
{"error": "internal server error"}
```

No stack trace is exposed to the client.

---

## 8. Unknown Route

**What happens:** Flask's 404 error handler returns:
```json
{"error": "not found"}
```
with `Content-Type: application/json`. No HTML error pages.
