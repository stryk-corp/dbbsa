#!/usr/bin/env bash
set -e

# Simple entrypoint to wait for DB, run migrations, ensure superuser, then start gunicorn
RETRIES=${MIGRATE_RETRIES:-30}
SLEEP_SECONDS=${MIGRATE_SLEEP:-3}

echo "Starting entrypoint: will try migrations up to ${RETRIES} times..."
count=0
function check_db() {
  echo "Checking DB connectivity..."
  python - <<'PY'
from django.db import connections
from django.db.utils import OperationalError
import sys
try:
    conn = connections['default']
    c = conn.cursor()
    print('DB connection OK')
except OperationalError as e:
    print('DB OperationalError:', e)
    sys.exit(2)
except Exception as e:
    print('DB connection test failed:', repr(e))
    sys.exit(3)
PY
  return $?
}
until ( check_db && python manage.py migrate --noinput ); do
  count=$((count+1))
  if [ "$count" -ge "$RETRIES" ]; then
    echo "Migrations failed after $count attempts. Exiting."
    exit 1
  fi
  echo "Migration attempt $count failed — waiting ${SLEEP_SECONDS}s before retrying..."
  sleep $SLEEP_SECONDS
done

echo "Migrations applied successfully. Ensuring superuser exists..."
python manage.py ensure_superuser || true

echo "Starting Gunicorn..."
exec gunicorn neural_village.wsgi:application --bind 0.0.0.0:${PORT:-8000}
