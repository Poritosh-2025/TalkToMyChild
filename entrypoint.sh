#!/bin/bash
set -e

echo "Running migrations..."
python manage.py migrate --noinput

if [ "$1" = "worker" ]; then
    echo "Starting Celery Worker..."
    exec celery -A config worker --loglevel=info --concurrency=4
fi

if [ "$1" = "beat" ]; then
    echo "Starting Celery Beat..."
    exec celery -A config beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
fi

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>/dev/null || true

echo "Starting Gunicorn..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:12004 \
    --workers 5 \
    --threads 4 \
    --timeout 180 \
    --max-requests 1000 \
    --max-requests-jitter 50 \
    --access-logfile -