"""
Extracción multimodal de metadatos con Google Gemini (docs/06_GEMINI_AI_PIPELINE.md).

El modelo recibe el PDF/imagen y devuelve exclusivamente un JSON con el esquema
definido en EXTRACTION_RESPONSE_SCHEMA. Cualquier desvío se normaliza aquí para
que el resto del pipeline trabaje siempre con un diccionario predecible.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)

AI_DOCUMENT_TYPES = ("POLIZA", "FACTURA", "SERVICIO_PUBLICO", "CARTA_SOLICITUD", "ACTA_ENTREGA", "OTRO")

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
""".strip()

EXTRACTION_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "OBJECT",
    "properties": {
        "contract_number": {"type": "STRING", "nullable": True},
        "client_identification": {"type": "STRING", "nullable": True},
        "client_name": {"type": "STRING", "nullable": True},
        "document_type": {"type": "STRING", "enum": list(AI_DOCUMENT_TYPES)},
        "document_date": {"type": "STRING", "nullable": True},
        "expiration_date": {"type": "STRING", "nullable": True},
        "extracted_text_summary": {"type": "STRING"},
        "confidence_score": {"type": "NUMBER"},
    },
    "required": ["document_type", "confidence_score", "extracted_text_summary"],
}

EXPECTED_KEYS = tuple(EXTRACTION_RESPONSE_SCHEMA["properties"].keys())


class AIExtractionError(Exception):
    """Fallo transitorio o de formato al consultar el modelo (reintentable)."""


class AIConfigurationError(AIExtractionError):
    """La integración con Gemini no está configurada (sin API key). No reintentable."""


def _clamp_confidence(value) -> float:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, score))


def _clean_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() in {"null", "none", "n/a", "na"}:
        return None
    return text


def normalize_extraction(raw: dict[str, Any] | None) -> dict[str, Any]:
    """Garantiza todas las llaves, tipos coherentes y valores dentro de rango."""
    raw = raw or {}
    document_type = (_clean_str(raw.get("document_type")) or "OTRO").upper()
    if document_type not in AI_DOCUMENT_TYPES:
        document_type = "OTRO"

    return {
        "contract_number": _clean_str(raw.get("contract_number")),
        "client_identification": _clean_str(raw.get("client_identification")),
        "client_name": _clean_str(raw.get("client_name")),
        "document_type": document_type,
        "document_date": _clean_str(raw.get("document_date")),
        "expiration_date": _clean_str(raw.get("expiration_date")),
        "extracted_text_summary": _clean_str(raw.get("extracted_text_summary")) or "",
        "confidence_score": _clamp_confidence(raw.get("confidence_score")),
    }


def parse_model_json(text: str) -> dict[str, Any]:
    """Interpreta la respuesta del modelo tolerando fences ```json ... ```."""
    if not text or not text.strip():
        raise AIExtractionError("Gemini devolvió una respuesta vacía.")
    cleaned = text.strip()
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, flags=re.DOTALL)
    if fence:
        cleaned = fence.group(1)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIExtractionError(f"Respuesta de Gemini no es JSON válido: {exc}") from exc
    if not isinstance(data, dict):
        raise AIExtractionError("Respuesta de Gemini no es un objeto JSON.")
    return data


TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "429", "RESOURCE_EXHAUSTED", "high demand", "overloaded")


def is_transient_model_error(exc: Exception) -> bool:
    """Saturación o cuota del modelo: vale la pena probar el modelo de respaldo de inmediato."""
    text = str(exc)
    return any(marker in text for marker in TRANSIENT_MARKERS)


class GeminiExtractor:
    """Adaptador sobre el SDK oficial `google-genai`.

    Si el modelo principal responde con saturación (503/429) se intenta una vez el
    modelo de respaldo (`GEMINI_FALLBACK_MODEL`) antes de delegar el reintento a Celery.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None, fallback_model: str | None = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL
        self.fallback_model = (
            fallback_model if fallback_model is not None else getattr(settings, "GEMINI_FALLBACK_MODEL", "")
        ) or None
        self._client = None

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
            except ImportError as exc:  # pragma: no cover
                raise AIConfigurationError("El paquete google-genai no está instalado.") from exc
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def extract(self, file_bytes: bytes, mime_type: str) -> dict[str, Any]:
        if not self.is_configured:
            raise AIConfigurationError("GEMINI_API_KEY no está configurada.")

        try:
            return self._generate(self.model, file_bytes, mime_type)
        except AIExtractionError as primary_error:
            fallback = self.fallback_model
            if not fallback or fallback == self.model or not is_transient_model_error(primary_error):
                raise
            logger.warning("Modelo %s saturado; intentando respaldo %s", self.model, fallback)
            try:
                data = self._generate(fallback, file_bytes, mime_type)
            except AIExtractionError:
                raise primary_error
            data["model_used"] = fallback
            return data

    def _generate(self, model: str, file_bytes: bytes, mime_type: str) -> dict[str, Any]:
        from google.genai import types

        client = self._get_client()
        try:
            response = client.models.generate_content(
                model=model,
                contents=[
                    EXTRACTION_SYSTEM_PROMPT,
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=EXTRACTION_RESPONSE_SCHEMA,
                    temperature=0.0,
                ),
            )
        except Exception as exc:
            raise AIExtractionError(f"Error consultando Gemini ({model}): {exc}") from exc

        raw = parse_model_json(getattr(response, "text", "") or "")
        data = normalize_extraction(raw)
        data["model_used"] = model
        return data


def extract_document_metadata(file_bytes: bytes, mime_type: str) -> dict[str, Any]:
    """Punto de entrada usado por la tarea Celery."""
    return GeminiExtractor().extract(file_bytes, mime_type)
