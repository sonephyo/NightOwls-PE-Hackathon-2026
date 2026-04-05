# API Documentation

Base URL: `http://localhost:5000`

All responses are JSON. All timestamps are ISO 8601 format.

---

## Health

### GET /health

Check if the API is running.

**Request:** No payload

**Response: 200 OK**
```json
{
  "status": "ok"
}
```

---

## Users

### GET /users

List all users. Supports optional pagination.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `page` | integer | No | Page number |
| `per_page` | integer | No | Results per page |

**Response: 200 OK**
```json
[
  {
    "id": 1,
    "username": "silvertrail15",
    "email": "silvertrail15@hackstack.io",
    "created_at": "2025-09-19T22:25:05"
  }
]
```

---

### GET /users/\<id\>

Get a single user by ID.

**Response: 200 OK**
```json
{
  "id": 1,
  "username": "silvertrail15",
  "email": "silvertrail15@hackstack.io",
  "created_at": "2025-09-19T22:25:05"
}
```

**Response: 404 Not Found** — user does not exist

---

### POST /users

Create a new user.

**Request Body:**
```json
{
  "username": "testuser",
  "email": "testuser@example.com"
}
```

**Response: 201 Created**
```json
{
  "id": 3,
  "username": "testuser",
  "email": "testuser@example.com",
  "created_at": "2026-04-03T12:00:00"
}
```

**Response: 400 Bad Request / 422 Unprocessable Entity** — invalid data (e.g. integer for username)

---

### POST /users/bulk

Bulk import users from a CSV file.

**Request:** `multipart/form-data` with a `file` field containing `users.csv`

**Response: 200 OK or 201 Created**
```json
{ "count": 2 }
// OR
{ "imported": 2 }
// OR array of imported objects
```

---

### PUT /users/\<id\>

Update an existing user.

**Request Body:**
```json
{
  "username": "updated_username"
}
```

**Response: 200 OK**
```json
{
  "id": 1,
  "username": "updated_username",
  "email": "silvertrail15@hackstack.io",
  "created_at": "2025-09-19T22:25:05"
}
```

---

## URLs

### GET /urls

List all shortened URLs. Supports optional filtering.

**Query Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `user_id` | integer | No | Filter by user |

**Response: 200 OK**
```json
[
  {
    "id": 1,
    "user_id": 1,
    "short_code": "ALQRog",
    "original_url": "https://opswise.net/harbor/journey/1",
    "title": "Service guide lagoon",
    "is_active": true,
    "created_at": "2025-06-04T00:07:00",
    "updated_at": "2025-11-19T03:17:29"
  }
]
```

---

### GET /urls/\<id\>

Get a single URL by ID.

**Response: 200 OK**
```json
{
  "id": 1,
  "user_id": 1,
  "short_code": "ALQRog",
  "original_url": "https://opswise.net/harbor/journey/1",
  "title": "Service guide lagoon",
  "is_active": true,
  "created_at": "2025-06-04T00:07:00",
  "updated_at": "2025-11-19T03:17:29"
}
```

**Response: 404 Not Found** — URL does not exist

---

### POST /urls

Create a new shortened URL.

**Request Body:**
```json
{
  "user_id": 1,
  "original_url": "https://example.com/test",
  "title": "Test URL"
}
```

**Response: 201 Created**
```json
{
  "id": 3,
  "user_id": 1,
  "short_code": "k8Jd9s",
  "original_url": "https://example.com/test",
  "title": "Test URL",
  "is_active": true,
  "created_at": "2026-04-03T12:00:00",
  "updated_at": "2026-04-03T12:00:00"
}
```

**Response: 404 Not Found** — user_id does not exist
**Response: 400 Bad Request** — invalid constraints

---

### PUT /urls/\<id\>

Update a URL's title or active status.

**Request Body:**
```json
{
  "title": "Updated Title",
  "is_active": false
}
```

**Response: 200 OK**
```json
{
  "id": 1,
  "user_id": 1,
  "short_code": "ALQRog",
  "original_url": "https://opswise.net/harbor/journey/1",
  "title": "Updated Title",
  "is_active": false,
  "created_at": "2025-06-04T00:07:00",
  "updated_at": "2026-04-03T12:00:00"
}
```

---

## Events / Analytics

### GET /events

List all analytics events.

**Response: 200 OK**
```json
[
  {
    "id": 1,
    "url_id": 1,
    "user_id": 1,
    "event_type": "created",
    "timestamp": "2025-06-04T00:07:00",
    "details": {
      "short_code": "ALQRog",
      "original_url": "https://opswise.net/harbor/journey/1"
    }
  }
]
```

---

## Error Reference

| Status Code | Meaning |
|---|---|
| `200 OK` | Success |
| `201 Created` | Resource created |
| `400 Bad Request` | Invalid input |
| `404 Not Found` | Resource not found |
| `422 Unprocessable Entity` | Valid JSON but failed validation |
