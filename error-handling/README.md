# Error Handling Documentation

This folder documents how the URL shortener handles errors, bad input, and failure scenarios.

---

## Files

| File | Description |
|------|-------------|
| [status-codes.md](status-codes.md) | Every HTTP status code the API returns and what triggers it |
| [failure-modes.md](failure-modes.md) | What breaks, what the app does, and how to recover |
| [validation-rules.md](validation-rules.md) | Input validation rules for every endpoint |

---

## Quick Summary

| Scenario | Status Code |
|----------|------------|
| Success (read) | 200 |
| Success (create) | 201 |
| Redirect | 302 |
| Bad input / wrong type / missing field | 400 |
| Resource not found / inactive URL / deleted URL | 404 |
| Server error | 500 |

The app never returns HTML error pages — all errors are JSON with an `error` key.
