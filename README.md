# URL Shortener — MLH PE Hackathon 2026

A production-style URL shortener backend built for the MLH Production Engineering Hackathon. No frontend — pure backend service with a focus on reliability, observability, and documentation.

**Stack:** Flask · Peewee ORM · PostgreSQL · uv

---

## Prerequisites

- **uv** — Python package manager (handles versions, virtualenvs, dependencies)

  ```bash
  # macOS / Linux
  curl -LsSf https://astral.sh/uv/install.sh | sh

  # Windows (PowerShell)
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

- **PostgreSQL** running locally (Docker or local install both work)

---

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd <repo-name>

# 2. Install dependencies
uv sync

# 3. Create the database
createdb hackathon_db

# 4. Configure environment
cp .env.example .env
# Edit .env if your DB credentials differ from the defaults

# 5. Load seed data
# Download seed files from https://mlh-pe-hackathon.com and follow platform instructions

# 6. Run the server
uv run run.py

# 7. Verify it's running
curl http://localhost:5000/health
# → {"status":"ok"}
```

---

## Project Structure

```
.
├── app/
│   ├── __init__.py          # App factory (create_app)
│   ├── database.py          # DB connection, BaseModel, teardown hooks
│   ├── models/
│   │   └── __init__.py      # Register models here
│   └── routes/
│       └── __init__.py      # Register blueprints here
├── .env.example             # Environment variable template
├── .gitignore
├── .python-version          # Python version pin for uv
├── pyproject.toml           # Project metadata and dependencies
├── run.py                   # Entry point — use `uv run run.py`
└── README.md
```

---

## Environment Variables

Copy `.env.example` to `.env` and update as needed:

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://localhost/hackathon_db` | PostgreSQL connection string |

---

## API Endpoints

> Full API documentation coming in Silver tier. Below are the currently implemented endpoints.

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status":"ok"}` |

_More endpoints will be documented as the team builds them out._

---

## Team

| Name | Track |
|---|---|
| Aaron | Reliability |
| _(teammate)_ | Observability |
| Cameron | Documentation |

---

## Hackathon

- **Event:** MLH Production Engineering Hackathon 2026
- **Dates:** April 3–5, 2026
- **Track:** Documentation
- **Template:** [MLH-Fellowship/PE-Hackathon-Template-2026](https://github.com/MLH-Fellowship/PE-Hackathon-Template-2026)
