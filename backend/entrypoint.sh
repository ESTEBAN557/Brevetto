#!/bin/sh
set -e

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

exec "$@"
