"""
Filtros facetados de documentos (US-018 / US-022).

Parámetros de consulta soportados por GET /api/v1/documents/:
  q                         búsqueda rápida: radicado, archivo, remitente, contrato, razón social (full-text
                            en español) y NIT/cédula (ignora puntos y guiones)
  processing_status / status  estado exacto o lista separada por comas
  source_channel / channel   canal exacto o lista separada por comas
  category                   categoría documental (lista separada por comas)
  document_type / document_type_code
  contract / contract_number / client / client_identification / digital_record
  created_from / created_to  rango de fecha de radicación (fecha local, inclusivo)
  document_date_from / document_date_to
  expiration_from / expiration_to
  expiring_within_days       vence en los próximos N días (incluye vencidos si include_expired=true)
  expired                    true => ya vencidos; false => vigentes con fecha
  has_contract               true/false
  min_confidence / max_confidence
  registered_by              username
"""
from __future__ import annotations

import re
from datetime import timedelta

import django_filters as filters
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import F, Q, Value
from django.db.models.functions import Replace
from django.utils import timezone

from apps.documents.models import Document

FTS_CONFIG = "spanish"


class CharInFilter(filters.BaseInFilter, filters.CharFilter):
    """Lista separada por comas: ?status=RECIBIDO,PROCESANDO"""


def normalize_digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def annotate_client_identification(queryset, field_path: str):
    """Añade `client_id_normalized` (sin puntos ni guiones) para comparar NIT/cédulas."""
    return queryset.annotate(
        client_id_normalized=Replace(
            Replace(F(field_path), Value("."), Value("")),
            Value("-"),
            Value(""),
        )
    )


class DocumentFilter(filters.FilterSet):
    q = filters.CharFilter(method="filter_q", label="Búsqueda rápida")

    processing_status = filters.ChoiceFilter(choices=Document.ProcessingStatus.choices)
    status = CharInFilter(field_name="processing_status", lookup_expr="in")
    source_channel = filters.ChoiceFilter(choices=Document.SourceChannel.choices)
    channel = CharInFilter(field_name="source_channel", lookup_expr="in")

    document_type = filters.UUIDFilter(field_name="document_type_id")
    document_type_code = filters.CharFilter(field_name="document_type__code", lookup_expr="iexact")
    category = CharInFilter(field_name="document_type__category", lookup_expr="in")

    digital_record = filters.UUIDFilter(field_name="digital_record_id")
    contract = filters.UUIDFilter(field_name="digital_record__contract_id")
    contract_number = filters.CharFilter(
        field_name="digital_record__contract__contract_number", lookup_expr="iexact"
    )
    client = filters.UUIDFilter(field_name="digital_record__contract__client_id")
    client_identification = filters.CharFilter(method="filter_client_identification")
    has_contract = filters.BooleanFilter(method="filter_has_contract")

    created_from = filters.DateFilter(field_name="created_at", lookup_expr="date__gte")
    created_to = filters.DateFilter(field_name="created_at", lookup_expr="date__lte")
    document_date_from = filters.DateFilter(field_name="document_date", lookup_expr="gte")
    document_date_to = filters.DateFilter(field_name="document_date", lookup_expr="lte")
    expiration_from = filters.DateFilter(field_name="expiration_date", lookup_expr="gte")
    expiration_to = filters.DateFilter(field_name="expiration_date", lookup_expr="lte")
    expiring_within_days = filters.NumberFilter(method="filter_expiring_within_days")
    include_expired = filters.BooleanFilter(method="noop")
    expired = filters.BooleanFilter(method="filter_expired")

    min_confidence = filters.NumberFilter(field_name="ai_confidence_score", lookup_expr="gte")
    max_confidence = filters.NumberFilter(field_name="ai_confidence_score", lookup_expr="lte")
    registered_by = filters.CharFilter(field_name="registered_by__username", lookup_expr="iexact")

    class Meta:
        model = Document
        fields: list[str] = []

    # ------------------------------------------------------------------ métodos --
    def noop(self, queryset, name, value):
        return queryset

    def filter_q(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        condition = (
            Q(filing_number__icontains=term)
            | Q(original_filename__icontains=term)
            | Q(external_sender_name__icontains=term)
            | Q(digital_record__contract__contract_number__icontains=term)
            | Q(digital_record__contract__client__name__icontains=term)
            | Q(digital_record__contract__client__email__icontains=term)
        )
        queryset = queryset.annotate(
            client_fts=SearchVector("digital_record__contract__client__name", config=FTS_CONFIG)
        )
        condition |= Q(client_fts=SearchQuery(term, config=FTS_CONFIG, search_type="plain"))

        digits = normalize_digits(term)
        if len(digits) >= 4:
            queryset = annotate_client_identification(
                queryset, "digital_record__contract__client__identification_number"
            )
            condition |= Q(client_id_normalized__icontains=digits)
        return queryset.filter(condition).distinct()

    def filter_client_identification(self, queryset, name, value):
        digits = normalize_digits(value)
        if not digits:
            return queryset
        return annotate_client_identification(
            queryset, "digital_record__contract__client__identification_number"
        ).filter(client_id_normalized__startswith=digits)

    def filter_has_contract(self, queryset, name, value):
        return queryset.filter(digital_record__isnull=not value)

    def filter_expiring_within_days(self, queryset, name, value):
        try:
            days = max(0, int(value))
        except (TypeError, ValueError):
            return queryset
        today = timezone.localdate()
        limit = today + timedelta(days=days)
        include_expired = self.data.get("include_expired", "true")
        include_expired = str(include_expired).lower() not in ("false", "0", "no")
        condition = Q(expiration_date__isnull=False, expiration_date__lte=limit)
        if not include_expired:
            condition &= Q(expiration_date__gte=today)
        return queryset.filter(condition)

    def filter_expired(self, queryset, name, value):
        today = timezone.localdate()
        if value:
            return queryset.filter(expiration_date__lt=today)
        return queryset.filter(expiration_date__gte=today)
