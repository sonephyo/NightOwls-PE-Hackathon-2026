# Deploy Guide

How to get the URL shortener running in production and how to roll back if something goes wrong.

---

## Local Deployment

```bash
# 1. Clone the repo
git clone https://github.com/sonephyo/PE-Hackathon-Template-2026.git
cd PE-Hackathon-Template-2026

# 2. Install dependencies
uv sync

# 3. Create the database
createdb hackathon_db

# 4. Configure environment
cp .env.example .env
# Edit .env with your actual credentials

# 5. Load seed data
uv run load_seed.py

# 6. Start the server
uv run run.py
```

Verify it's running:
```bash
curl http://localhost:5000/health
# → {"status":"ok"}
```

---

## Environment Setup

All configuration is done via environment variables in `.env`. See [`docs/config.md`](config.md) for the full list.

Never commit `.env` to the repo — it's already in `.gitignore`.

---

## Stopping the Server

```bash
# Find the process
lsof -i :5000

# Kill it by PID
kill <PID>
```

Or just `Ctrl+C` if it's running in the foreground.

---

## Restarting the Server

```bash
# Stop it first (Ctrl+C or kill), then:
uv run run.py
```

---

## Rollback Procedure

If a bad commit breaks the app, roll back to the last working commit:

```bash
# See recent commits
git log --oneline -10

# Roll back to a specific commit (replace <hash> with the commit hash)
git checkout <hash>

# Reinstall dependencies in case anything changed
uv sync

# Restart the server
uv run run.py
```

To permanently revert the bad commit on your branch:
```bash
git revert <bad-commit-hash>
git push origin docs/cameron
```

---

## Checking Server Logs

If the server is running in the foreground, logs print directly to the terminal.

To capture logs to a file:
```bash
uv run run.py > logs/app.log 2>&1 &
```

Then tail the log:
```bash
tail -f logs/app.log
```

---

## Health Check

Always verify the server is up after any deploy or restart:

```bash
curl http://localhost:5000/health
# Expected: {"status":"ok"}
```

Any other response or connection error means the server is down.
