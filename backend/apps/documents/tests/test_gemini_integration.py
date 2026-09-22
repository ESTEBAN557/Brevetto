"""
Prueba de integración REAL contra Google Gemini (consume cuota de la API).

Se omite salvo que exista GEMINI_API_KEY y BREVETTO_RUN_INTEGRATION=1:

    BREVETTO_RUN_INTEGRATION=1 POSTGRES_HOST=localhost .venv/Scripts/python.exe -m pytest -m integration
"""
import os

import pytest
from django.conf import settings

from apps.documents.services.ai_extraction import GeminiExtractor, AI_DOCUMENT_TYPES
from scripts.make_sample_pdf import sample_pdf

pytestmark = pytest.mark.integration

RUN_INTEGRATION = os.environ.get("BREVETTO_RUN_INTEGRATION") == "1"


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Requiere BREVETTO_RUN_INTEGRATION=1 (llamada real a Gemini)")
def test_real_gemini_extracts_policy_metadata_from_pdf():
    if not settings.GEMINI_API_KEY:
        pytest.skip("GEMINI_API_KEY no configurada")

    data = GeminiExtractor().extract(sample_pdf("poliza"), "application/pdf")

    assert data["document_type"] in AI_DOCUMENT_TYPES
    assert data["document_type"] == "POLIZA"
    assert (data["contract_number"] or "").upper() == "CONT-2026-042"
    assert "9001234561".startswith((data["client_identification"] or "").replace("-", "")[:9])
    assert data["expiration_date"] == "2027-09-30"
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert data["extracted_text_summary"]
