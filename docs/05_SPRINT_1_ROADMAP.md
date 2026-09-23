# Roadmap y Tareas de Desarrollo — Sprint 1

Este documento contiene el desglose técnico y las tareas específicas para implementar las **8 Historias de Usuario seleccionadas para el Sprint 1** (Total: 19 Story Points).

---

## Matriz de Historias de Usuario de Sprint 1

| ID | Historia de Usuario | Épica | Pts | Responsable Principal |
| :--- | :--- | :--- | :---: | :--- |
| **US-001** | Generate Registration Number | Document Registration | 2 | Esteban Alvarez Garcia |
| **US-002** | Upload Digital Document | Document Registration | 3 | Juan David Ortiz Moncada |
| **US-004** | Create Document Record | Document Registration | 2 | Santiago Sanchez Lara |
| **US-005** | Capture Document Metadata | Document Registration | 2 | Esteban Alvarez Garcia |
| **US-006** | Record Registration Information | Document Registration | 2 | Isabella Bejarano López |
| **US-007** | Update Document Metadata | Document Registration | 2 | Felipe Giraldo Neira |
| **US-008** | Create Contract Folder | Document Registration | 3 | Juan David Ortiz Moncada |
| **US-009** | Process Document Content | Document Processing | 3 | Felipe Giraldo Neira |

---

## Desglose de Tareas de Implementación por Historia

### 1. US-001 — Generar Número de Radicado Único (2 pts)
- [x] Implementar modelo `FilingSequence` en Django con método `get_next_number(date)`.
- [x] Aplicar transacción atómica (`transaction.atomic()`) y bloqueo con `select_for_update()` para evitar duplicados concurrentes.
- [x] Crear tests unitarios en `pytest` simulando 10 llamadas concurrentes y validando que todos los radicados sean únicos y respeten el formato `RAD-YYYYMMDD-XXXXXX`.

### 2. US-002 — Subir Documento Digital (3 pts)
- [x] Configurar `django-storages` con backend para MinIO / AWS S3.
- [x] Crear endpoint `POST /api/v1/documents/upload/` admitiendo multipart/form-data.
- [x] Validar extensiones permitidas (`.pdf`, `.png`, `.jpg`) y límite de tamaño (máx. 25MB).
- [x] Calcular checksum SHA-256 del archivo al recibirlo.

### 3. US-004 — Crear Registro de Documento (2 pts)
- [x] Crear modelo `Document` con estado inicial `RECIBIDO`.
- [x] Asociar el número de radicado generado en `US-001` al registro.
- [x] Registrar tamaño en bytes, nombre original y mime-type.

### 4. US-005 — Capturar Metadatos del Documento (2 pts)
- [x] Campos en modelo para canal de origen (`source_channel`), fecha del documento y remitente.
- [x] Serializadores DRF para validar metadatos obligatorios y opcionales.

### 5. US-006 — Registrar Información de Radicación (2 pts)
- [x] Guardar timestamp automático UTC y hora local (`America/Bogota`).
- [x] Guardar usuario autenticado que realizó la radicación.
- [x] Emitir primer registro en la tabla `AuditLog` con la acción `CARGA`.

### 6. US-007 — Actualizar Metadatos del Documento (2 pts)
- [x] Endpoint `PATCH /api/v1/documents/{id}/metadata/` para actualizar tipo documental o fecha de vencimiento.
- [x] Registrar en `AuditLog` el cambio efectuado con el estado anterior y el nuevo estado.

### 7. US-008 — Crear Carpeta / Expediente de Contrato (3 pts)
- [x] Modelos `Client`, `Contract` y `DigitalRecord`.
- [x] Servicio que crea automáticamente la carpeta digital en S3 cuando se registra un contrato nuevo.
- [x] Endpoint `POST /api/v1/contracts/` con generación de expediente.

### 8. US-009 — Procesar Contenido del Documento (3 pts)
- [x] Configuración de Celery con Redis broker en `config/celery.py`.
- [x] Tarea `tasks.process_document_content_task(document_id)` que actualiza el estado a `PROCESANDO`.
- [x] Disparo asíncrono inmediato al completar `US-002`.
- [x] Manejo de errores y reintentos ante fallos de conexión.
