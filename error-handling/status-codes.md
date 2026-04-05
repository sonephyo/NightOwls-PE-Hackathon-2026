# HTTP Status Codes Reference

Every status code the API returns, what triggers it, and what the client should do.

---

## 200 OK
Returned on successful GET and PUT requests.

**Endpoints:** GET /urls, GET /users, GET /events, PUT /urls/<id>, PUT /users/<id>

---

## 201 Created
Returned when a resource is successfully created.

**Endpoints:** POST /urls, POST /users, POST /events, POST /urls/bulk, POST /users/bulk, POST /events/bulk

---

## 302 Found (Redirect)
Returned when a valid, active short code is hit.

**Endpoint:** GET /<short_code>

The `Location` header contains the destination URL. The client is redirected automatically.

---

## 400 Bad Request
Returned when the request body is malformed, missing required fields, contains wrong types, or includes unknown fields.

**Common causes:**
- Body is not a JSON object (string, list, null)
- Required field missing (`original_url`, `user_id`, `event_type`)
- Wrong type (`user_id` must be an integer, not a string or boolean)
- Unknown/extra fields in the request body
- Invalid values (`is_active` must be a boolean, `short_code` must be alphanumeric and ≤10 chars)
- Invalid URL format (must be `http://` or `https://`)

**Response format:**
```json
{"error": "<description of what was wrong>"}
```

---

## 404 Not Found
Returned when a referenced resource does not exist, or when a URL is inactive/deleted and should leave no trace.

**Triggers:**
- `GET /urls/<id>` — URL with that ID does not exist
- `GET /users/<id>` — User with that ID does not exist
- `GET /events/<id>` — Event with that ID does not exist
- `GET /urls/<short_code>` — Short code not found
- `GET /<short_code>` — Short code not found, URL is inactive, or URL has been deleted
- `PUT /urls/<id>` — URL not found
- `DELETE /urls/<id>` — URL not found
- `PUT /users/<id>` — User not found
- `DELETE /users/<id>` — User not found
- `POST /urls` — `user_id` does not reference an existing user
- `POST /events` — `url_id` or `user_id` does not reference an existing resource
- Any unknown route

**Why 404 for inactive URLs?**
Returning 410 (Gone) would reveal that the URL once existed — a "footprint." 404 is intentional: a dormant route should offer no passage and leave no trace.

**Response format:**
```json
{"error": "not found"}
```

---

## 500 Internal Server Error
Returned when an unhandled exception occurs.

**Common causes:**
- Database connection lost mid-request
- Unexpected data type from DB
- Unhandled edge case in application code

**Response format:**
```json
{"error": "internal server error"}
```

The full traceback is logged server-side via structlog. The client only sees the generic message — no stack trace is leaked.
