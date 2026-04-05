# Troubleshooting

Common issues and how to fix them. If X happens, try Y.

---

## Server won't start

**Symptom:** `uv run run.py` errors out immediately.

**Try:**
```bash
# Check if port 5000 is already in use
lsof -i :5000

# If something is using it, kill it
kill <PID>

# Then restart
uv run run.py
```

---

## Database connection error

**Symptom:** `OperationalError: could not connect to server` or similar.

**Try:**
```bash
# Check if PostgreSQL is running
pg_isready

# If not, start it (macOS)
brew services start postgresql

# Verify your .env credentials match your local postgres setup
cat .env
```

Make sure `DATABASE_NAME`, `DATABASE_HOST`, `DATABASE_PORT`, `DATABASE_USER`, and `DATABASE_PASSWORD` are all correct.

---

## Database doesn't exist

**Symptom:** `FATAL: database "hackathon_db" does not exist`

**Try:**
```bash
createdb hackathon_db
```

---

## Seed data won't load

**Symptom:** `uv run load_seed.py` errors or loads 0 rows.

**Try:**
- Make sure the DB exists first (`createdb hackathon_db`)
- Make sure the tables exist (models must be created before seeding)
- Check that `users.csv`, `urls.csv`, and `events.csv` are in the repo root

---

## GET /health returns nothing / connection refused

**Symptom:** `curl http://localhost:5000/health` fails.

**Try:**
- Make sure the server is actually running (`uv run run.py`)
- Check the terminal for errors on startup
- Make sure you're hitting port 5000, not another port

---

## 404 on a valid endpoint

**Symptom:** Hitting `/users` or `/urls` returns 404.

**Try:**
- The route may not be registered yet — check `app/routes/__init__.py`
- Make sure the blueprint was imported and added via `app.register_blueprint(...)`

---

## 500 Internal Server Error

**Symptom:** Any endpoint returns 500.

**Try:**
- Check the terminal where the server is running — Flask prints the full traceback there
- Most common causes: DB not connected, missing env var, bad data in request body

---

## uv command not found

**Symptom:** `zsh: command not found: uv`

**Try:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# Then restart your terminal or run:
source ~/.zshrc
```

---

## Changes not reflected after editing code

**Symptom:** You edited a file but the server still shows old behavior.

**Try:**
- Flask does not auto-reload by default — stop the server (`Ctrl+C`) and restart it
- Or enable debug mode: set `FLASK_DEBUG=1` in your `.env`
