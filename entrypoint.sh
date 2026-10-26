#!/bin/sh
set -eu

# The container starts as root only long enough to make the SQLite volume
# writable, then drops to the unprivileged app user.
mkdir -p /app/data
chown -R app:app /app/data

gosu app python manage.py migrate --noinput

WORKERS=${GUNICORN_WORKERS:-3}

# The container always listens on 8000 internally. The host-facing port is
# controlled by APP_PORT in .env (see docker-compose.yml).
exec gosu app gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "$WORKERS" \
    --worker-class sync \
    --timeout 30 \
    --graceful-timeout 30 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --access-logfile -
