# Input Validation Rules

All validation happens at the route level before any DB operation.

---

## POST /users

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| username | Yes | string | Non-empty, non-whitespace |
| email | Yes | string | Non-empty, must contain `@`, must be unique |

Unknown fields → 400.

---

## POST /urls

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| original_url | Yes | string | Must be valid `http://` or `https://` URL |
| user_id | Yes | integer | Must reference an existing user (not bool, not string) |
| title | No | string | Must be a string if provided |
| short_code | No | string | Alphanumeric only, max 10 chars, non-empty |
| is_active | No | boolean | Must be `true` or `false` (not string) |

Unknown fields → 400.

If `short_code` conflicts → a new unique code is auto-generated (no error).

---

## PUT /urls/<id>

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| original_url | No | string | Must be valid `http://` or `https://` URL |
| title | No | string | Must be a string if provided |
| is_active | No | boolean | Must be `true` or `false` |

At least one field required. Unknown fields → 400.

---

## POST /events

| Field | Required | Type | Rules |
|-------|----------|------|-------|
| url_id | Yes | integer | Must reference an existing URL (not bool) |
| event_type | Yes | string | Non-empty, non-whitespace |
| user_id | No | integer | Must reference an existing user if provided (not bool) |
| details | No | object | Must be a JSON object (dict), not string/list/integer |

Unknown fields → 400.

---

## GET /<short_code> (redirect)

| Param | Required | Type | Rules |
|-------|----------|------|-------|
| user_id | No | integer | Must be a valid integer if provided |

If `user_id` is not a valid integer → 400, no redirect, no event created.
If `user_id` references unknown user → 400, no redirect, no event created.
If URL is inactive or deleted → 404, no redirect, no event created.

---

## General Rules

- Request body must be a JSON object (`{}`), not a string, list, or null → 400
- Wrong `Content-Type` (not `application/json`) → 400 or 415
- All "resource not found" cases (valid ID format but doesn't exist) → 404
- All "bad format" cases (wrong type, missing field) → 400
