# 🏛️ Brevetto — Sistema Inteligente de Gestión Documental

Plataforma inteligente de automatización, radicación, clasificación asistida por IA y consulta de expedientes digitales para **Coltebienes S.A.**

---

## 🚀 Arquitectura y Tecnologías
- **Frontend:** Next.js (App Router), React, TypeScript.
- **Backend:** Python 3.11+, Django 5, Django REST Framework, Celery 5.
- **Base de Datos:** PostgreSQL 16.
- **Broker & Queue:** Redis 7.
- **Almacenamiento de Objetos:** AWS S3 / MinIO.
- **Motor de Inteligencia Artificial:** Google Gemini API (Multimodal OCR & Clasificación).
- **Contenedores:** Docker & Docker Compose.
---

## 📖 Documentación del Proyecto
Toda la especificación técnica y de arquitectura se encuentra en la carpeta [`/docs`](docs/):
* [`docs/01_COLTEBIENES_CONTEXT.md`](docs/01_COLTEBIENES_CONTEXT.md): Situación actual y las 6 funcionalidades requeridas por Coltebienes.
* [`docs/02_ARCHITECTURE_AND_STACK.md`](docs/02_ARCHITECTURE_AND_STACK.md): Diagrama de arquitectura por capas y servicios Docker.
* [`docs/03_DATABASE_MODELS.md`](docs/03_DATABASE_MODELS.md): Modelos relacionales en Django ORM.
* [`docs/04_API_SPECIFICATION.md`](docs/04_API_SPECIFICATION.md): Contratos de endpoints REST, payloads y códigos de respuesta.
* [`docs/05_SPRINT_1_ROADMAP.md`](docs/05_SPRINT_1_ROADMAP.md): Checklist de tareas e historias de usuario de Sprint 1.
* [`docs/06_GEMINI_AI_PIPELINE.md`](docs/06_GEMINI_AI_PIPELINE.md): Pipeline de Celery con Google Gemini y lógica Human-in-the-Loop.

---

## ⚡ Comandos de Inicio Rápido

### 1. Iniciar los servicios con Docker:
```bash
docker compose up -d --build
```

### 2. Ejecutar migraciones de base de datos:
```bash
docker compose exec backend python manage.py migrate
```

### 3. Ejecutar la suite de pruebas del backend (requiere el contenedor `db` activo):
```bash
docker compose up -d db redis minio
cd backend
uv venv .venv --python 3.12 && uv pip install --python .venv/Scripts/python.exe -r requirements.txt
POSTGRES_HOST=localhost .venv/Scripts/python.exe -m pytest -v
```

### 4. Servicios y puertos del entorno local

| Servicio | URL / Puerto | Credenciales dev (.env.example) |
| :--- | :--- | :--- |
| API Django | http://localhost:8000/api/v1/health/ | JWT en `/api/v1/auth/token/` |
| Admin Django | http://localhost:8000/admin/ | crear con `manage.py createsuperuser` |
| Frontend Next.js | http://localhost:3000 | — |
| PostgreSQL 16 | localhost:5432 | brevetto / brevetto |
| Redis 7 | localhost:6379 | — |
| MinIO API / Consola | http://localhost:9000 / http://localhost:9001 | minioadmin / minioadmin |

> La imagen de MinIO se descarga desde `quay.io/minio/minio` porque Docker Hub ya no publica `minio/minio`.

### 5. Endpoints implementados (Sprint 1, autenticación JWT `Authorization: Bearer <token>`)

| Método | Ruta | Descripción |
| :--- | :--- | :--- |
| POST | `/api/v1/auth/token/` | Obtiene access/refresh JWT |
| POST | `/api/v1/documents/upload/` | Radica un documento (multipart) y encola el análisis IA |
| POST | `/api/v1/documents/batch-upload/` | Radica varios documentos en un envío (202) |
| GET | `/api/v1/documents/` · `/{id}/` | Listado paginado con filtros/búsqueda y detalle |
| GET | `/api/v1/documents/pending-review/` | Bandeja Human-in-the-Loop (`REQUIERE_REVISION`) |
| POST | `/api/v1/documents/{id}/validate/` | Confirmación humana: asocia contrato y tipo, archiva |
| PATCH | `/api/v1/documents/{id}/metadata/` | Actualiza metadatos con antes/después en `AuditLog` |
| GET | `/api/v1/documents/{id}/view-url/` · `download-url/` | URL prefirmada (15 min) + registro de consulta/descarga |
| GET | `/api/v1/documents/{id}/audit-trail/` | Historial inmutable del documento |
| GET/POST/PATCH | `/api/v1/contracts/` | Contratos; al crear se genera expediente y carpeta en S3 |
| GET | `/api/v1/contracts/{id}/documents/` · `audit-trail/` | Expediente digital y su historial |
| GET/POST/PATCH | `/api/v1/clients/` | Clientes (sin DELETE: integridad referencial) |
| GET | `/api/v1/document-types/` | Catálogo documental sembrado por migración |

Pipeline IA: `documents.process_document_content` (Celery) descarga el archivo de MinIO, consulta Gemini con salida JSON estructurada y aplica la regla HITL (`AI_CONFIDENCE_THRESHOLD=0.85`). Sin `GEMINI_API_KEY` el documento pasa directamente a revisión manual.

### 6. Interfaces web (Fase 5)

| Ruta | Descripción |
| :--- | :--- |
| `/login` | Ingreso del personal (JWT) |
| `/admin` | Bandeja de ingesta en tiempo real: contadores por estado, búsqueda, filtros y sondeo cada 5 s |
| `/admin/upload` | Radicación individual o por lote con arrastrar-y-soltar y contrato opcional |
| `/admin/review` · `/admin/review/{id}` | Bandeja HITL y validación en pantalla dividida (visor PDF + sugerencias IA + formulario) |
| `/admin/documents/{id}` | Ficha del documento, edición de metadatos, descarga segura e historial de auditoría |
| `/admin/contracts` · `/admin/contracts/{id}` | Contratos, alta con cliente nuevo o existente, expediente agrupado por categoría y auditoría |
| `/portal/radicacion` | Portal público del inquilino: valida contrato + NIT, radica y descarga/imprime el comprobante |

API del portal público (sin JWT, con throttling y token temporal firmado de 30 min):
`POST /api/v1/portal/verify-contract/` y `POST /api/v1/portal/submit-document/`.

**Modelos Gemini:** `gemini-1.5-flash` y la familia 2.x fueron retirados. Por defecto se usa `gemini-3.5-flash` con
respaldo inmediato en `gemini-3-flash-preview` ante 503/429 (`GEMINI_FALLBACK_MODEL`). La prueba de integración real se
ejecuta con `BREVETTO_RUN_INTEGRATION=1 ... pytest -m integration`.

**Resiliencia del pipeline:** la tarea reintenta 3 veces con backoff ante fallos transitorios, Celery restaura los mensajes no confirmados al reiniciar el worker (`acks_late`), y el worker corre Celery beat (`-B`) con `documents.requeue_stale_documents`, que cada 5 minutos re-encola documentos sin avance en `RECIBIDO`/`PROCESANDO` durante más de 15 minutos (`PROCESSING_STALE_AFTER_MINUTES`).
