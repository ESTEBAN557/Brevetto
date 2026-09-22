# Brevetto

Base ejecutable del sistema de gestión documental para Coltebienes S.A.

Este primer bloque contiene la arquitectura de ejecución y los puntos de extensión. Las historias de usuario se incorporarán después como funcionalidades independientes en `backend/apps` y `frontend/app`.

## Inicio local

1. Copiar `.env.example` como `.env`.
2. Ejecutar `docker compose up -d --build`.
3. Consultar el backend en `http://localhost:8000/api/v1/health/`.
4. Consultar el frontend en `http://localhost:3000`.

## Estructura

- `backend/config`: configuración Django, ASGI, WSGI y Celery.
- `backend/apps`: paquetes Django vacíos preparados para las historias.
- `frontend/app`: shell inicial de Next.js.
- `docker-compose.yml`: PostgreSQL, Redis, MinIO, backend, worker y frontend.

Los archivos `.env` reales y los artefactos locales están excluidos del control de versiones.
