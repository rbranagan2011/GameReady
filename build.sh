#!/usr/bin/env bash
# Build script for Render deployment
# Ensures binary wheels are used when available

set -o errexit  # Exit on error

# Upgrade pip to latest version
pip install --upgrade pip

# Install requirements, preferring binary wheels
pip install --only-binary :all: -r requirements.txt || pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

