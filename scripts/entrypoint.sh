r#!/bin/bash

set -e  

echo "Waiting for Redis..."

until redis-cli -h ${BLOG_REDIS_HOST:-redis} -p ${BLOG_REDIS_PORT:-6379} ping > /dev/null 2>&1; do
    echo "Redis is unavailable - sleeping"
    sleep 2
done

echo "✓ Redis is up"

mkdir -p /app/logs
chown -R appuser:appuser /app/logs || true

echo "Running migrations..."
python manage.py migrate --noinput

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Compiling translations..."
python manage.py compilemessages

# if BLOG_SEED_DB=true, then run the seed command to populate the database with initial data
if [ "$BLOG_SEED_DB" = "true" ]; then
    echo "Seeding database..."
    python manage.py seed || echo "Seed command failed or data already exists"
fi

echo "Starting application..."

exec "$@"