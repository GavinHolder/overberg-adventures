#!/bin/bash
set -e

echo "Running database migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "Seeding site data..."
python manage.py seed_site

echo "Starting application..."
exec "$@"
