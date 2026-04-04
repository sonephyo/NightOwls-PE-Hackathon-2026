# Configuration

All environment variables used by this application.

---

## Setup

Copy the example file and edit it:

```bash
cp .env.example .env
```

Never commit `.env` to the repo — it's in `.gitignore`.

---

## Environment Variables

| Variable | Default | Required | Description |
|---|---|---|---|
| `DATABASE_NAME` | `hackathon_db` | Yes | Name of the PostgreSQL database |
| `DATABASE_HOST` | `localhost` | Yes | Host where PostgreSQL is running |
| `DATABASE_PORT` | `5432` | Yes | Port PostgreSQL listens on |
| `DATABASE_USER` | `postgres` | Yes | PostgreSQL username |
| `DATABASE_PASSWORD` | `postgres` | Yes | PostgreSQL password |
| `FLASK_DEBUG` | `0` | No | Set to `1` to enable auto-reload and debug output |

---

## Example .env

```env
DATABASE_NAME=hackathon_db
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=postgres
FLASK_DEBUG=0
```

---

## Notes

- `DATABASE_HOST` should be `localhost` for local development. If using Docker, this may be the container name instead.
- `FLASK_DEBUG=1` enables Flask's auto-reloader and detailed error pages. Never use this in production.
- All variables are loaded at startup via `python-dotenv`. Changes to `.env` require a server restart to take effect.
