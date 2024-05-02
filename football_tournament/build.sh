#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install -r ../requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations
python manage.py migrate

# Check if the superuser exists and create if not
if ! python manage.py checksuperuser; then
    python manage.py createsuperuser --no-input
fi

# Deactivate the virtual environment
deactivate
