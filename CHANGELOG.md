# Registro de Cambios (Changelog) — Brevetto

Todos los cambios notables en este proyecto serán documentados en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.0.0/),
y este proyecto se adhiere a [Semantic Versioning](https://semver.org/lang/es/).

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
