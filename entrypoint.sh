#!/bin/sh
set -e

mkdir -p /app/data

echo "Running database migrations..."
dbmate --url "${DATABASE_URL}" up

echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 2>&1 | tee -a /app/data/app.log
