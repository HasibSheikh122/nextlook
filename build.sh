#!/bin/bash
set -o errexit  # Script crash holei execution bondho kore dibe

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --noinput

# Apply database migrations
# python manage.py makemigrations --noinput

python manage.py migrate --noinput