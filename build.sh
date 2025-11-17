#!/usr/bin/env bash
# Build script for Render deployment
# Ensures binary wheels are used when available

set -o errexit  # Exit on error

# Upgrade pip to latest version
pip install --upgrade pip

# Install requirements, preferring binary wheels
pip install --only-binary :all: -r requirements.txt || pip install -r requirements.txt

# Create media directory structure (if not using persistent disk)
# Note: Persistent disk at /opt/render/project/src/media should already exist
# But ensure team_logos subdirectory exists and has correct permissions
if [ -d "/opt/render/project/src/media" ]; then
    mkdir -p /opt/render/project/src/media/team_logos
    chmod -R 775 /opt/render/project/src/media
else
    mkdir -p media/team_logos
fi

# Create cache table (required for django-ratelimit with database cache)
python manage.py createcachetable django_cache_table || true

# Collect static files
python manage.py collectstatic --noinput

