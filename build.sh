#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -o errexit

echo "--- Starting Deployment Process ---"

# Upgrade pip to the latest version
echo "Upgrading pip..."
pip install --upgrade pip

# Install project dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files for production
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

echo "--- Deployment Finished Successfully! ---"