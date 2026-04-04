# Decision Log

Why we made the technical choices we did. This document exists so future engineers understand the reasoning, not just the result.

---

## Flask (web framework)

**Decision:** Use Flask over Django, FastAPI, or other frameworks.

**Why:** Flask is minimal and unopinionated — it gives you routing and request handling without forcing a project structure. For a hackathon URL shortener with a focused scope, Django would be overkill (too much built-in we don't need) and FastAPI would add async complexity. Flask lets us move fast and stay readable.

---

## Peewee (ORM)

**Decision:** Use Peewee over SQLAlchemy or raw SQL.

**Why:** Peewee is a lightweight ORM designed for smaller projects. SQLAlchemy is more powerful but significantly more complex to set up and reason about. Raw SQL would work but removes the safety and convenience of model-based queries. Peewee hits the sweet spot — simple models, clean queries, minimal boilerplate.

---

## PostgreSQL (database)

**Decision:** Use PostgreSQL over SQLite or MySQL.

**Why:** PostgreSQL is production-grade. SQLite is fine for local dev but not suitable for a service under load — it doesn't handle concurrent writes well. MySQL would also work but PostgreSQL has better support in the Python ecosystem and is the industry standard for this type of application. The hackathon template was also pre-wired for PostgreSQL.

---

## uv (package manager)

**Decision:** Use uv over pip or Poetry.

**Why:** uv handles Python version pinning, virtual environment creation, and dependency management in one tool. pip requires manual venv setup. Poetry adds complexity. uv is significantly faster than both and the template came pre-configured for it.

---

## No frontend

**Decision:** Build backend API only, no frontend.

**Why:** This is a Production Engineering hackathon — the focus is on reliability, observability, scalability, and documentation, not UI. A frontend would add scope without contributing to the judging criteria. All interaction happens via HTTP requests (curl, Postman, or a future frontend built by someone else).

---

## CSV seed files

**Decision:** Pre-populate the database from CSV files rather than building an admin UI or migration scripts.

**Why:** The hackathon platform provides seed CSV files (users, urls, events) as the standard data source. Loading from CSV is fast, repeatable, and easy to verify. It also matches the `POST /users/bulk` endpoint pattern — showing consistency between how data enters the system manually and programmatically.

---

## Markdown documentation in repo

**Decision:** Write all docs as Markdown files committed to the repository.

**Why:** The hackathon brief explicitly said "treat docs like code — if it isn't committed, it doesn't exist." Keeping docs in the repo means they version alongside the code, stay discoverable on GitHub, and can be reviewed in pull requests. This also feeds directly into Docusaurus for a rendered docs site.
