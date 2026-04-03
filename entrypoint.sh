#!/bin/sh
set -e

mkdir -p /app/data /app/midias

echo "Running database migrations..."
dbmate --url "${DATABASE_URL}" up

echo "Starting worker in background..."
uv run python -m app.worker &

echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
