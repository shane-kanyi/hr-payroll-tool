#!/bin/sh
set -e

echo "Applying database migrations..."
flask db upgrade

if [ -n "$ADMIN_EMAIL" ] && [ -n "$ADMIN_PASSWORD" ]; then
    echo "Ensuring an admin user exists..."
    flask create-admin --email "$ADMIN_EMAIL" --password "$ADMIN_PASSWORD" --if-not-exists
fi

exec "$@"
