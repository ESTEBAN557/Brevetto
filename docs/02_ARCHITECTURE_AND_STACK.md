# Arquitectura del Sistema y Stack Tecnológico — Brevetto

## 1. Visión General de la Arquitectura
Brevetto sigue una arquitectura desacoplada orientada a servicios y procesamiento asíncrono en segundo plano:

```text
[ Cliente Web / Inquilino ]        [ Personal Coltebienes ]
          │                                   │
          ▼                                   ▼
┌─────────────────────────────────────────────────────────┐
│              Capa de Presentación (Next.js)             │
│        - Portal Administrativo (Gestión / Validación)   │
│        - Portal Externo de Radicación (/portal/radicar) │
└───────────────────────────┬─────────────────────────────┘
                            │ HTTP / REST API (JSON)
                            ▼
┌─────────────────────────────────────────────────────────┐
│             Capa de Negocio (Django REST Framework)     │
│        - Autenticación JWT & RBAC                       │
│        - Controladores de Radicación y Expedientes      │
│        - Disparador de Tareas Asíncronas                │
└───────────────┬─────────────────────────┬───────────────┘
                │                         │ Encola tareas
                ▼                         ▼
   ┌─────────────────────────┐   ┌─────────────────────────┐
   │ PostgreSQL 16           │   │ Redis 7 (Message Broker)│
   │ - Entidades de Dominio  │   └────────────┬────────────┘
   │ - Secuencias Atómicas   │                │ Despacha
   │ - Auditoría Inmutable   │                ▼
   └─────────────────────────┘   ┌─────────────────────────┐
                                 │ Celery Workers          │
                                 │ - Carga en S3/MinIO     │
                                 │ - Extracción Gemini OCR │
                                 │ - Clasificación & HITL  │
                                 └────────────┬────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
        ┌─────────────────────────┐                       ┌─────────────────────────┐
        │ AWS S3 / MinIO Storage  │                       │ Google Gemini API       │
        │ - PDFs e Imágenes       │                       │ - IA Multimodal / OCR   │
        └─────────────────────────┘                       └─────────────────────────┘
```

---

## 2. Definición del Stack Tecnológico

| Componente | Tecnología | Versión | Propósito Principal |
| :--- | :--- | :--- | :--- |
| **Frontend** | Next.js (App Router), React, TypeScript | Next 14+ | Interfaces reactivas, visor PDF, portal web y tipado estricto. |
| **Backend API** | Python, Django, Django REST Framework | Python 3.11+, Django 5+ | Lógica de negocio, ORM relacional, APIs REST y control de acceso. |
| **Tareas Asíncronas** | Celery | 5.3+ | Procesamiento en segundo plano para mantener la API con respuesta < 2s. |
| **Broker de Mensajes** | Redis | 7.x | Cola de tareas distribuida y almacenamiento en caché. |
| **Base de Datos** | PostgreSQL | 16.x | Integridad referencial, secuencias de radicado y log de auditoría. |
| **Almacenamiento Objetos** | AWS S3 / MinIO | MinIO latest | Custodia escalable de documentos binarios (PDF/PNG). |
| **Motor de IA / OCR** | Google Gemini API (`google-genai`) | Gemini 3.5 Flash (1.5 y 2.x retirados) | Extracción de metadatos, OCR multimodal y clasificación de texto. |
| **Contenedores** | Docker & Docker Compose | Compose v2 | Paridad exacta entre entornos de desarrollo y producción. |

---

## 3. Servicios en Docker Compose (`docker-compose.yml`)

El proyecto debe orquestarse mediante 6 contenedores principales:
1. **`db`**: `postgres:16-alpine` (Puerto `5432:5432`).
2. **`redis`**: `redis:7-alpine` (Puerto `6379:6379`).
3. **`minio`**: `minio/minio:latest` (Puertos `9000:9000` API S3 y `9001:9001` Consola Web).
4. **`backend`**: `Dockerfile` de Django con `gunicorn` o `runserver` (Puerto `8000:8000`).
5. **`celery_worker`**: Mismo contenedor de backend ejecutando `celery -A config worker -l info`.
6. **`frontend`**: Next.js Node 20 (Puerto `3000:3000`).

---

## 4. Requerimientos No Funcionales (NFRs)
- **Latencia de Respuesta:** Endpoints de carga y consulta responden en menos de **2 segundos**. Todo procesamiento pesado pasa a Celery.
- **Concurrencia:** Soporte de 10 a 50 usuarios internos concurrentes y cientos de radicaciones externas diarias.
- **Inmutabilidad:** Números de radicado y registros de auditoría no pueden ser modificados ni eliminados.
- **Seguridad:** Tokens JWT, autenticación basada en roles (RBAC) y pre-signed URLs con expiración de 15 minutos para ver o descargar documentos.
