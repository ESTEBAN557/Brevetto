# Pipeline de Inteligencia Artificial con Google Gemini — Brevetto

Este documento describe la integración entre el worker de Celery y la API de **Google Gemini** para la extracción OCR multimodal y la clasificación documental inteligente.

---

## 1. SDK y Configuración
Se utiliza el SDK oficial de Google: `google-genai` (o `google-generativeai`).

```bash
pip install google-genai
```

Variables de entorno requeridas (`.env`):
```env
GEMINI_API_KEY=AIzaSy...
GEMINI_MODEL=gemini-3.5-flash
```

> **Nota (2026-09):** `gemini-1.5-flash` y la familia `gemini-2.x` fueron retirados de la API para nuevos usuarios. El modelo por defecto es `gemini-3.5-flash`; `gemini-3-flash-preview` responde más rápido (~6 s vs ~24 s por PDF) y sirve como alternativa. Ante errores 503 por demanda la tarea Celery reintenta automáticamente.

---

## 2. Prompt del Sistema y Esquema JSON Estructurado

El modelo debe forzarse a responder **exclusivamente con un JSON estructurado** siguiendo este esquema:

```python
EXTRACTION_SYSTEM_PROMPT = """
Eres el motor de análisis documental de Brevetto para la inmobiliaria Coltebienes S.A.
Tu tarea es analizar el documento adjunto (PDF o imagen) y extraer los metadatos clave para clasificarlo y asociarlo a un contrato de arrendamiento o venta de inmuebles.

Debes responder ÚNICAMENTE en formato JSON con la siguiente estructura:
{
  "contract_number": "string o null si no se encuentra explícitamente",
  "client_identification": "string (NIT o Cédula sin puntos ni guiones) o null",
  "client_name": "string (nombre de la empresa o persona) o null",
  "document_type": "string (uno de: POLIZA, FACTURA, SERVICIO_PUBLICO, CARTA_SOLICITUD, ACTA_ENTREGA, OTRO)",
  "document_date": "YYYY-MM-DD o null",
  "expiration_date": "YYYY-MM-DD si el documento tiene vigencia (ej. póliza), o null",
  "extracted_text_summary": "resumen en 2 líneas del contenido del documento",
  "confidence_score": float entre 0.0 y 1.0 indicando qué tan seguro estás de la clasificación
}
"""
```

---

## 3. Lógica del Worker de Celery (`tasks.py`)

```python
from celery import shared_task
from google import genai
from django.conf import settings
from .models import Document, Contract, DocumentType, AuditLog

@shared_task(bind=True, max_retries=3)
def process_document_content_task(self, document_id):
    try:
        doc = Document.objects.get(id=document_id)
        doc.processing_status = Document.ProcessingStatus.PROCESSING
        doc.save(update_fields=["processing_status"])

        # 1. Obtener bytes del archivo desde S3 / MinIO
        file_bytes = get_file_from_storage(doc.file_path)

        # 2. Llamada a Gemini Multimodal
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=[
                EXTRACTION_SYSTEM_PROMPT,
                genai.types.Part.from_bytes(data=file_bytes, mime_type=doc.mime_type)
            ],
            config=genai.types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        ai_data = json.loads(response.text)
        doc.ai_extracted_data = ai_data
        confidence = float(ai_data.get("confidence_score", 0.0))
        doc.ai_confidence_score = confidence

        # 3. Buscar coincidencia de contrato en BD
        contract_number = ai_data.get("contract_number")
        contract = None
        if contract_number:
            contract = Contract.objects.filter(contract_number__iexact=contract_number).first()

        # 4. Regla Human-in-the-Loop (HITL)
        if confidence >= 0.85 and contract is not None:
            # Clasificación automática exitosa
            doc.digital_record = contract.digital_record
            doc.processing_status = Document.ProcessingStatus.PROCESSED
            AuditLog.objects.create(
                document=doc,
                action=AuditLog.Action.AI_CLASSIFY,
                details={"confidence": confidence, "auto_associated": True}
            )
        else:
            # Requiere revisión del personal en la bandeja
            doc.processing_status = Document.ProcessingStatus.NEEDS_REVIEW
            AuditLog.objects.create(
                document=doc,
                action=AuditLog.Action.AI_CLASSIFY,
                details={"confidence": confidence, "needs_human_validation": True}
            )

        doc.save()

    except Exception as exc:
        doc.processing_status = Document.ProcessingStatus.FAILED
        doc.save(update_fields=["processing_status"])
        raise self.retry(exc=exc, countdown=30)
```
