#!/bin/sh
set -e

echo "Running database seed..."
uv run seed.py

echo "Starting server..."
exec uv run gunicorn --workers 4 --timeout 30 --keep-alive 2 --max-requests 1000 --max-requests-jitter 50 --bind 0.0.0.0:8000 run:app
