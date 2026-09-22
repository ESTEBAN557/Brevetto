# Registro de Cambios (Changelog) — Brevetto

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

---

## [0.3.0] - Sprint 2 (Búsqueda Avanzada, Alertas de Vencimiento y Datos de Demostración) - 2026-09-21

### ✨ Añadido (Added)
- **Búsqueda y Filtros Avanzados (`US-018`, `US-022`):**
  - `DocumentFilter` (`apps/documents/filters.py`) con búsqueda facetada en `GET /api/v1/documents/`: búsqueda rápida `q` (radicado, archivo, remitente, contrato, razón social con *full-text search* en español y NIT/cédula normalizado sin puntos ni guiones), listas separadas por comas en `status`, `channel` y `category`, rangos de fechas `created_from/created_to`, `document_date_from/to`, `expiration_from/to`, `expiring_within_days` + `include_expired`, `expired`, `has_contract`, `contract`, `contract_number`, `client`, `client_identification`, `min_confidence/max_confidence` y `registered_by`.
  - `ContractFilter` y `ClientFilter` (`apps/core/filters.py`): `q` full-text por razón social, NIT normalizado, número de contrato y dirección; `status` múltiple, `start_from/to`, `end_from/to`, `expiring_within_days`, `expired` y `has_documents`.
  - Nuevos campos de ordenamiento (`document_date`, `filing_number`).
  - Frontend: barra de búsqueda rápida y panel de filtros avanzados (estado, canal, categoría, rango de radicación, rango de vencimiento) en `/admin`; filtros por estado, vencimiento de contrato, rango de fecha de fin y expedientes con/sin documentos en `/admin/contracts`.
- **Sistema de Alertas y Vencimientos (Requerimiento Coltebienes #6):**
  - Servicio `apps/documents/services/expirations.py` con etapas `warning` (≤ 30 días), `critical` (≤ 7 días) y `expired`.
  - Tarea periódica de Celery beat `documents.check_expiring_documents` (cada 6 h, configurable con `EXPIRATION_CHECK_SECONDS`) que registra la alerta en `AuditLog` con la nueva acción `ALERTA_VENCIMIENTO`, una sola vez por documento y etapa, incluyendo datos de contacto del inquilino (correo y teléfono) para gestionar la renovación.
  - Endpoint `GET /api/v1/documents/expiring/?days=30&include_expired=true` con conteos de vencidos/por vencer y, en cada documento, `days_to_expiration`, `expiration_stage`, `client_email` y `client_phone`.
  - Frontend: tarjeta "Documentos próximos a vencer" en el dashboard `/admin` con insignias visuales por etapa (vencido / crítico / aviso), contacto del inquilino y acceso directo al documento y al expediente.
- **Datos Semilla de Demostración:**
  - Comando `python manage.py seed_demo_data` (`apps/core/management/commands/seed_demo_data.py`), idempotente: usuario `demo`, 3 clientes con NIT realistas, 3 contratos activos (Bodega Guayabal, Local El Poblado, Centro Logístico Calle 80) con expediente en MinIO, y 5 documentos con PDF real generado por `scripts/make_sample_pdf.py` (póliza por vencer, factura, certificado vencido, carta en revisión por baja confianza y póliza en revisión por contrato desconocido), con auditoría coherente y alertas de vencimiento precalculadas.
  - Nueva plantilla `certificado` (Cámara de Comercio) en el generador de PDFs.
- **Pruebas:** nuevas suites `test_filters.py`, `test_expirations.py` y `test_seed_demo_data.py`; la suite completa se mantiene al 100 %.

### 🔄 Cambiado (Changed)
- `DocumentViewSet`, `ContractViewSet` y `ClientViewSet` reemplazan `filterset_fields` por `FilterSet` dedicados (compatibles con los parámetros del Sprint 1).
- `DocumentSerializer` expone `client_email`, `client_phone`, `days_to_expiration` y `expiration_stage`.
- Migración `documents.0003_auditlog_expiration_alert_action` (nueva opción de acción en la bitácora).

---

## [0.2.0] - Sprint 1 (Implementación MVP y Pipeline Documental) - 2026-09-21

### ✨ Añadido (Added)
- **Infraestructura y Contenedores (Fase 1):**
  - Orquestación con `docker-compose.yml` para 6 servicios: `db` (PostgreSQL 16), `redis` (Redis 7), `minio` (S3 Object Storage), `backend` (Django 5), `celery_worker` y `frontend` (Next.js 14).
  - Healthchecks automáticos y comando `ensure_storage_bucket` para MinIO.
- **Modelos de Dominio y Datos (Fase 2):**
  - Modelos relacionales: `Client`, `Contract`, `DigitalRecord`, `DocumentType`, `Document` y `AuditLog`.
  - Migración con catálogo inicial de tipos documentales (`0002_seed_document_types.py`).
  - Generador atómico de números de radicado único (`US-001`) con formato `RAD-YYYYMMDD-XXXXXX` y bloqueo `select_for_update`.
  - Trigger nativo en PostgreSQL para garantizar la inmutabilidad de la tabla `AuditLog` (`0002_auditlog_immutability_triggers.py`).
- **Endpoints REST API (Fase 3):**
  - Autenticación segura mediante JWT (`/api/v1/auth/token/`).
  - Radicación individual con cálculo de hash SHA-256 (`POST /api/v1/documents/upload/`).
  - Radicación en lote asíncrona (`POST /api/v1/documents/batch-upload/`).
  - Bandeja de documentos pendientes de validación (`GET /api/v1/documents/pending-review/`).
  - Validación y aprobación humana (*Human-in-the-Loop*) (`POST /api/v1/documents/{id}/validate/`).
  - Visualización y descarga segura mediante URLs prefirmadas de S3 con TTL de 15 minutos (`GET /api/v1/documents/{id}/view-url/`).
  - Consulta de historial de auditoría por documento y expediente (`GET .../audit-trail/`).
  - CRUD de clientes y contratos con creación automática de expedientes digitales.
- **Pipeline Asíncrono de Inteligencia Artificial (Fase 4):**
  - Tarea en Celery `process_document_content_task` integrada con Google Gemini API (`gemini-3.5-flash` y fallback).
  - Extracción OCR multimodal estructurada en JSON (número de contrato, NIT, tipo documental, fechas y score de confianza).
  - Lógica *Human-in-the-Loop*: auto-asociación si `confidence >= 0.85`, o enrutamiento a revisión manual si es menor.
  - Tarea periódica de Celery Beat `requeue_stale_documents` para recuperación ante fallos de worker.
- **Frontend y Portales Web (Fase 5):**
  - Portal administrativo con Next.js 14 App Router:
    - `/login`: Autenticación con JWT.
    - `/admin`: Dashboard con métricas de ingesta en tiempo real y sondeo cada 5s.
    - `/admin/upload`: Radicación con arrastrar y soltar (*drag & drop*).
    - `/admin/review/[id]`: Interfaz de pantalla dividida (visor PDF + sugerencias IA + aprobación en 1 clic).
    - `/admin/contracts`: Expediente digital organizado por categoría documental.
    - `/admin/documents/[id]`: Ficha técnica y línea de tiempo de auditoría.
  - Portal público para inquilinos (`/portal/radicacion`):
    - Verificación de contrato y NIT con rate-limiting y token temporal firmado.
    - Carga directa de soportes (pólizas, facturas) y generación de comprobante de radicación digital.
- **Pruebas y Calidad de Software:**
  - Suite de 139 pruebas automatizadas en `pytest` con 100% de aprobación en unitarias, APIs y tareas Celery.

---

## [0.1.0] - Sprint 0 (Definición del Producto, Arquitectura y Requerimientos) - 2026-08-05

### ✨ Añadido (Added)
- **Definición de Negocio y Necesidades:**
  - Levantamiento del problema de Coltebienes S.A. y análisis del flujo manual existente.
  - Matriz de 33 Requerimientos Funcionales (`RF-01` a `RF-33`) y especificación de NFRs.
  - Glosario de términos de dominio inmobiliario y documental.
  - Análisis competitivo frente a Microsoft SharePoint/Syntex, Alfresco y plataformas IDP (Kofax/ABBYY).
- **Planificación Ágil y Backlog:**
  - User Story Mapping en Miro vinculando actividades, tareas e historias.
  - Product Backlog oficial con 27 Historias de Usuario (`US-001` a `US-027`), priorización MoSCoW y estimación en 85 Story Points.
  - Planificación del Sprint 1 seleccionando 8 historias clave de ingesta y radicación.
- **Diseño Arquitectónico y Prototipos:**
  - Definición del stack tecnológico desacoplado (Next.js, Django REST, Celery, Redis, PostgreSQL, S3, Gemini).
  - Diagrama de componentes por capas y flujo documental en Mermaid.
  - Modelo de dominio conceptual y clases de entidad.
  - Prototipo interactivo en Figma/HTML y sesión de validación de usuario con casos de prueba de aceptación.
- **Estándares de Ingeniería:**
  - Estrategia de ramas Git Flow / GitHub Flow.
  - Guías de estilo y convenciones de nomenclatura (PEP 8, ESLint, Prettier).
  - Pipelines de integración continua en GitHub Actions y análisis estático con Ruff, mypy y Bandit.
