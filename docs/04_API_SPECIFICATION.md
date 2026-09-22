# Especificación de la API REST — Brevetto

Todos los endpoints deben respetar el prefijo `/api/v1/` y responder en formato JSON.

---

## 1. Módulo de Radicación y Documentos (`/api/v1/documents/`)

### 1.1 Carga y Radicación Individual
* **Método / Ruta:** `POST /api/v1/documents/upload/`
* **Content-Type:** `multipart/form-data`
* **Permisos:** Autenticado (Personal Coltebienes)
* **Payload:**
  - `file`: Archivo binario (PDF, PNG, JPG). Máximo 25MB.
  - `source_channel`: `FISICO_ESCANEADO` | `DIGITAL_INTERNO`
  - `contract_id` (opcional): UUID si el usuario ya conoce el contrato.
* **Respuesta Exitosa (`201 Created`):**
```json
{
  "id": "7b8e5c1a-3d2f-4a6b-9c8e-1f2e3d4c5b6a",
  "filing_number": "RAD-20260920-000001",
  "original_filename": "cuenta_cobro_sep.pdf",
  "file_size_bytes": 1048576,
  "source_channel": "DIGITAL_INTERNO",
  "processing_status": "RECIBIDO",
  "created_at": "2026-09-20T20:45:00Z"
}
```
* **Efecto secundario:** Encola la tarea `process_document_content_task.delay(document_id)` en Celery.

---

### 1.2 Carga de Múltiples Documentos en Lote (`US-011`)
* **Método / Ruta:** `POST /api/v1/documents/batch-upload/`
* **Content-Type:** `multipart/form-data`
* **Payload:**
  - `files`: Lista de archivos binarios.
* **Respuesta (`202 Accepted`):**
```json
{
  "message": "3 documentos recibidos para radicación y procesamiento asíncrono.",
  "items": [
    {"filing_number": "RAD-20260920-000002", "filename": "doc1.pdf", "status": "RECIBIDO"},
    {"filing_number": "RAD-20260920-000003", "filename": "doc2.pdf", "status": "RECIBIDO"},
    {"filing_number": "RAD-20260920-000004", "filename": "doc3.pdf", "status": "RECIBIDO"}
  ]
}
```

---

### 1.3 Bandeja de Validación Humana (*Human-in-the-Loop*)
* **Método / Ruta:** `GET /api/v1/documents/pending-review/`
* **Respuesta:** Lista de documentos con `processing_status = 'REQUIERE_REVISION'`, incluyendo datos sugeridos por la IA y su `confidence_score`.

* **Confirmación / Corrección Humana:** `POST /api/v1/documents/{id}/validate/`
* **Payload:**
```json
{
  "contract_id": "9a1b2c3d-4e5f-6a7b-8c9d-0e1f2a3b4c5d",
  "document_type_id": "f1e2d3c4-b5a6-7890-1234-56789abcdef0",
  "expiration_date": "2027-09-20"
}
```
* **Respuesta:** `200 OK` (Actualiza estado a `PROCESADO`, asocia al expediente y registra en `AuditLog`).

---

### 1.4 Visualización y Descarga Segura
* **Obtener URL prefirmada de visualización:** `GET /api/v1/documents/{id}/view-url/`
* **Respuesta (`200 OK`):**
```json
{
  "filing_number": "RAD-20260920-000001",
  "view_url": "https://minio.coltebienes.local/brevetto-docs/...X-Amz-Signature=...",
  "expires_in_seconds": 900
}
```

---

## 2. Módulo del Portal Web Externo (`/api/v1/portal/`)

### 2.1 Validación de Inquilino
* **Método / Ruta:** `POST /api/v1/portal/verify-contract/`
* **Payload:**
```json
{
  "contract_number": "CONT-2026-042",
  "identification_number": "900123456-1"
}
```
* **Respuesta (`200 OK`):** Retorna token temporal de sesión de portal con información de la propiedad arrendada y documentos requeridos/pendientes.

### 2.2 Radicación Pública por Inquilino
* **Método / Ruta:** `POST /api/v1/portal/submit-document/`
* **Payload:**
  - `file`: PDF de la póliza o comunicación.
  - `document_type_code`: `POLIZA_CUMPLIMIENTO`
  - `sender_name`: Nombre de la persona que radica.
* **Respuesta (`201 Created`):** Retorna comprobante de radicación digital con fecha, hora, número de radicado y firma digital.

---

## 3. Módulo de Auditoría (`/api/v1/audit/`)

* **Listar historial de un documento:** `GET /api/v1/documents/{id}/audit-trail/`
* **Listar historial de un expediente:** `GET /api/v1/contracts/{id}/audit-trail/`
