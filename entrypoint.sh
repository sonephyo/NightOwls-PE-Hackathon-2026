#!/bin/sh
set -e

echo "Running database seed..."
uv run seed.py

echo "Starting server..."
# gthread workers: each worker spawns --threads threads for concurrent I/O
# 4 workers x 4 threads = 16 concurrent per replica
# worker-tmp-dir on RAM disk avoids slow disk I/O for heartbeat files
exec uv run gunicorn \
  --workers 4 \
  --worker-class gthread \
  --threads 8 \
  --timeout 60 \
  --keep-alive 5 \
  --max-requests 2000 \
  --max-requests-jitter 200 \
  --worker-tmp-dir /dev/shm \
  --bind 0.0.0.0:8000 \
  run:app
