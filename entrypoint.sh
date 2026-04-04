#!/bin/sh
set -e

echo "Running database seed..."
uv run seed.py

echo "Starting server..."
exec uv run gunicorn --workers 2 --timeout 120 --bind 0.0.0.0:8000 run:app
