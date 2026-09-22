#!/bin/sh
# Entrypoint del servicio backend: aplica migraciones, garantiza el bucket S3
# y finalmente ejecuta el comando recibido (runserver / gunicorn).
set -e

echo "[entrypoint] Aplicando migraciones..."
python manage.py migrate --noinput

echo "[entrypoint] Verificando bucket de almacenamiento..."
python manage.py ensure_storage_bucket || echo "[entrypoint] Aviso: no se pudo verificar el bucket (MinIO no disponible?)"

exec "$@"
