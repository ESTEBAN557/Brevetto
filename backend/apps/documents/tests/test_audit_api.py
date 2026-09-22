"""Pruebas del módulo global de auditoría GET /api/v1/audit/ (US-023, US-024, US-025)."""
from datetime import datetime, timezone as dt_timezone
from unittest.mock import patch

import pytest

from apps.documents.models import AuditLog, Document
from apps.documents.services.audit import log_action

AUDIT = "/api/v1/audit/"

T1 = datetime(2026, 9, 20, 15, 0, tzinfo=dt_timezone.utc)   # 10:00 Bogotá, 20 sep
T2 = datetime(2026, 9, 20, 16, 0, tzinfo=dt_timezone.utc)   # 11:00 Bogotá, 20 sep
T3 = datetime(2026, 9, 21, 14, 0, tzinfo=dt_timezone.utc)   # 09:00 Bogotá, 21 sep
T4 = datetime(2026, 9, 21, 20, 30, tzinfo=dt_timezone.utc)  # 15:30 Bogotá, 21 sep


class FakeRequest:
    def __init__(self, ip, user=None):
        self.META = {"REMOTE_ADDR": ip, "HTTP_USER_AGENT": "pytest"}
        self.user = user


@pytest.fixture
def audit_dataset(document, contract, user):
    document.digital_record = contract.digital_record
    document.save()
    orphan = Document.objects.create(
        filing_number="RAD-20260921-000077",
        file_path="x/orphan.pdf",
        original_filename="orphan.pdf",
        file_hash="f" * 64,
        file_size_bytes=10,
    )
    entries = {}
    with patch("django.utils.timezone.now", return_value=T1):
        entries["upload"] = log_action(document, AuditLog.Action.UPLOAD, request=FakeRequest("10.0.0.1", user), details={"filing_number": document.filing_number, "file_hash": "a" * 64})
    with patch("django.utils.timezone.now", return_value=T2):
        entries["ai"] = log_action(document, AuditLog.Action.AI_CLASSIFY, details={"confidence": 0.42, "reason": "low_confidence", "needs_human_validation": True})
    with patch("django.utils.timezone.now", return_value=T3):
        entries["view"] = log_action(orphan, AuditLog.Action.VIEW, request=FakeRequest("192.168.1.20", user), details={"storage_key": "x/orphan.pdf"})
    with patch("django.utils.timezone.now", return_value=T4):
        entries["download"] = log_action(document, AuditLog.Action.DOWNLOAD, request=FakeRequest("10.0.0.1", user), details={"export_type": "full_record_zip", "document_count": 3})
    return {"document": document, "orphan": orphan, **entries}


def actions_of(response):
    body = response.json()
    return [e["action"] for e in body["results"]]


@pytest.mark.django_db
class TestAuditListing:
    def test_list_is_paginated_newest_first_and_marked_immutable(self, api_client, audit_dataset):
        response = api_client.get(AUDIT)

        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 4
        assert actions_of(response) == ["DESCARGA", "CONSULTA_VISUAL", "CLASIFICACION_IA", "CARGA"]
        first = body["results"][0]
        assert first["immutable"] is True
        assert first["filing_number"] == audit_dataset["document"].filing_number
        assert first["contract_number"] == "CONT-2026-042"
        assert first["original_filename"] == "cuenta_cobro_sep.pdf"
        assert first["performed_by"] == "analista"
        assert first["action_label"] == "Descarga de Archivo"
        assert first["details"]["export_type"] == "full_record_zip"

    def test_retrieve_single_event(self, api_client, audit_dataset):
        response = api_client.get(f"{AUDIT}{audit_dataset['ai'].pk}/")
        assert response.status_code == 200
        assert response.json()["performed_by"] is None
        assert response.json()["details"]["reason"] == "low_confidence"

    def test_ordering_can_be_reversed(self, api_client, audit_dataset):
        assert actions_of(api_client.get(AUDIT, {"ordering": "timestamp"})) == ["CARGA", "CLASIFICACION_IA", "CONSULTA_VISUAL", "DESCARGA"]

    def test_requires_authentication(self, anonymous_client, audit_dataset):
        assert anonymous_client.get(AUDIT).status_code == 401


@pytest.mark.django_db
class TestAuditFilters:
    def test_filter_by_action_list(self, api_client, audit_dataset):
        assert actions_of(api_client.get(AUDIT, {"action": "CARGA"})) == ["CARGA"]
        assert actions_of(api_client.get(AUDIT, {"action": "CARGA,DESCARGA"})) == ["DESCARGA", "CARGA"]

    def test_filter_by_performed_by_and_system(self, api_client, audit_dataset):
        assert api_client.get(AUDIT, {"performed_by": "analista"}).json()["count"] == 3
        assert api_client.get(AUDIT, {"performed_by": "ANALISTA"}).json()["count"] == 3
        assert actions_of(api_client.get(AUDIT, {"performed_by": "system"})) == ["CLASIFICACION_IA"]
        assert api_client.get(AUDIT, {"performed_by": "nadie"}).json()["count"] == 0

    def test_filter_by_filing_number_document_and_contract(self, api_client, audit_dataset):
        doc = audit_dataset["document"]
        assert api_client.get(AUDIT, {"filing_number": doc.filing_number.lower()}).json()["count"] == 3
        assert api_client.get(AUDIT, {"document": str(audit_dataset["orphan"].pk)}).json()["count"] == 1
        assert api_client.get(AUDIT, {"contract_number": "cont-2026-042"}).json()["count"] == 3
        assert api_client.get(AUDIT, {"contract_number": "CONT-9999"}).json()["count"] == 0

    def test_filter_by_ip_address(self, api_client, audit_dataset):
        assert api_client.get(AUDIT, {"ip_address": "10.0.0.1"}).json()["count"] == 2
        assert actions_of(api_client.get(AUDIT, {"ip_address": "192.168.1.20"})) == ["CONSULTA_VISUAL"]

    def test_filter_by_timestamp_range_with_dates(self, api_client, audit_dataset):
        assert actions_of(api_client.get(AUDIT, {"timestamp_from": "2026-09-21"})) == ["DESCARGA", "CONSULTA_VISUAL"]
        assert actions_of(api_client.get(AUDIT, {"timestamp_to": "2026-09-20"})) == ["CLASIFICACION_IA", "CARGA"]
        assert api_client.get(AUDIT, {"timestamp_from": "2026-09-20", "timestamp_to": "2026-09-21"}).json()["count"] == 4
        assert api_client.get(AUDIT, {"timestamp_from": "2026-09-22"}).json()["count"] == 0

    def test_filter_by_timestamp_range_with_datetimes(self, api_client, audit_dataset):
        # Entre las 10:30 y las 12:00 hora Bogotá del 20 de septiembre solo cae la clasificación IA.
        response = api_client.get(AUDIT, {"timestamp_from": "2026-09-20T10:30:00-05:00", "timestamp_to": "2026-09-20T12:00:00-05:00"})
        assert actions_of(response) == ["CLASIFICACION_IA"]

    def test_invalid_timestamp_returns_400(self, api_client, audit_dataset):
        response = api_client.get(AUDIT, {"timestamp_from": "ayer"})
        assert response.status_code == 400
        assert "timestamp_from" in response.json()

    def test_text_search_inside_details_and_related_fields(self, api_client, audit_dataset):
        assert actions_of(api_client.get(AUDIT, {"q": "low_confidence"})) == ["CLASIFICACION_IA"]
        assert actions_of(api_client.get(AUDIT, {"q": "full_record_zip"})) == ["DESCARGA"]
        assert api_client.get(AUDIT, {"q": "orphan"}).json()["count"] == 1
        assert api_client.get(AUDIT, {"q": "CONT-2026-042"}).json()["count"] == 3
        assert api_client.get(AUDIT, {"q": "analista"}).json()["count"] == 3

    def test_filters_combine(self, api_client, audit_dataset):
        response = api_client.get(AUDIT, {"performed_by": "analista", "timestamp_from": "2026-09-21", "action": "DESCARGA,CONSULTA_VISUAL", "ip_address": "10.0.0.1"})
        assert actions_of(response) == ["DESCARGA"]

    def test_actions_catalog_with_counts_respects_filters(self, api_client, audit_dataset):
        catalog = {item["code"]: item for item in api_client.get(f"{AUDIT}actions/").json()}
        assert catalog["CARGA"]["count"] == 1
        assert catalog["ALERTA_VENCIMIENTO"]["count"] == 0
        assert catalog["DESCARGA"]["label"] == "Descarga de Archivo"

        filtered = {item["code"]: item["count"] for item in api_client.get(f"{AUDIT}actions/", {"performed_by": "system"}).json()}
        assert filtered["CLASIFICACION_IA"] == 1 and filtered["CARGA"] == 0


@pytest.mark.django_db
class TestAuditIsReadOnly:
    def test_write_methods_are_rejected(self, api_client, audit_dataset):
        entry_url = f"{AUDIT}{audit_dataset['upload'].pk}/"
        assert api_client.post(AUDIT, {"action": "CARGA"}, format="json").status_code == 405
        assert api_client.put(entry_url, {"action": "DESCARGA"}, format="json").status_code == 405
        assert api_client.patch(entry_url, {"action": "DESCARGA"}, format="json").status_code == 405
        assert api_client.delete(entry_url).status_code == 405
        assert AuditLog.objects.count() == 4
