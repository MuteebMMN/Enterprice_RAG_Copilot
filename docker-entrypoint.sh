#!/bin/sh
set -e

if [ -z "$JWT_SECRET" ]; then
    echo "JWT_SECRET is not set. Pass your settings with: docker run --env-file .env ..." >&2
    exit 1
fi

mkdir -p "$(dirname "$HR_DB_PATH")" "$UPLOAD_DIR"

# First start: create the mock HR database. Later starts keep the existing one.
if [ ! -f "$HR_DB_PATH" ]; then
    python scripts/seed_hr_db.py
fi

# Creates accounts for any employee that doesn't have one yet.
# With SEED_PASSWORD set (recommended on Cloud Run) every new account gets that password and nothing
# is printed. Without it, random passwords are printed once in the container logs.
if [ -n "$SEED_PASSWORD" ]; then
    python scripts/seed_users.py --password "$SEED_PASSWORD"
else
    python scripts/seed_users.py
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8080}"
