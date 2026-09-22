"""
Filtros facetados de contratos y clientes (US-018 / US-022).

GET /api/v1/contracts/ admite:
  q                      número de contrato, razón social (full-text español), NIT/cédula normalizado,
                         correo y dirección del inmueble
  status                 estado o lista separada por comas
  client                 UUID del cliente
  client_identification  NIT/cédula (ignora puntos y guiones)
  start_from/start_to    rango de fecha de inicio
  end_from/end_to        rango de fecha de fin
  expiring_within_days   contratos que terminan en los próximos N días
  expired                true => contratos con fecha de fin pasada
  has_documents          true/false
"""
from __future__ import annotations

from datetime import timedelta

import django_filters as filters
from django.contrib.postgres.search import SearchQuery, SearchVector
from django.db.models import Count, Q
from django.utils import timezone

from apps.core.models import Client, Contract
from apps.documents.filters import (
    FTS_CONFIG,
    CharInFilter,
    annotate_client_identification,
    normalize_digits,
)


class ContractFilter(filters.FilterSet):
    q = filters.CharFilter(method="filter_q", label="Búsqueda rápida")
    status = CharInFilter(field_name="status", lookup_expr="in")
    client = filters.UUIDFilter(field_name="client_id")
    client_identification = filters.CharFilter(method="filter_client_identification")
    start_from = filters.DateFilter(field_name="start_date", lookup_expr="gte")
    start_to = filters.DateFilter(field_name="start_date", lookup_expr="lte")
    end_from = filters.DateFilter(field_name="end_date", lookup_expr="gte")
    end_to = filters.DateFilter(field_name="end_date", lookup_expr="lte")
    expiring_within_days = filters.NumberFilter(method="filter_expiring_within_days")
    expired = filters.BooleanFilter(method="filter_expired")
    has_documents = filters.BooleanFilter(method="filter_has_documents")

    class Meta:
        model = Contract
        fields: list[str] = []

    def filter_q(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        condition = (
            Q(contract_number__icontains=term)
            | Q(property_address__icontains=term)
            | Q(client__name__icontains=term)
            | Q(client__email__icontains=term)
        )
        queryset = queryset.annotate(client_fts=SearchVector("client__name", config=FTS_CONFIG))
        condition |= Q(client_fts=SearchQuery(term, config=FTS_CONFIG, search_type="plain"))
        digits = normalize_digits(term)
        if len(digits) >= 4:
            queryset = annotate_client_identification(queryset, "client__identification_number")
            condition |= Q(client_id_normalized__icontains=digits)
        return queryset.filter(condition).distinct()

    def filter_client_identification(self, queryset, name, value):
        digits = normalize_digits(value)
        if not digits:
            return queryset
        return annotate_client_identification(queryset, "client__identification_number").filter(
            client_id_normalized__startswith=digits
        )

    def filter_expiring_within_days(self, queryset, name, value):
        try:
            days = max(0, int(value))
        except (TypeError, ValueError):
            return queryset
        today = timezone.localdate()
        return queryset.filter(end_date__gte=today, end_date__lte=today + timedelta(days=days))

    def filter_expired(self, queryset, name, value):
        today = timezone.localdate()
        return queryset.filter(end_date__lt=today) if value else queryset.filter(end_date__gte=today)

    def filter_has_documents(self, queryset, name, value):
        # Meta.ordering no se aplica en consultas con GROUP BY: se fija el orden explícitamente.
        queryset = queryset.annotate(documents_total=Count("digital_record__documents")).order_by(
            *Contract._meta.ordering
        )
        return queryset.filter(documents_total__gt=0) if value else queryset.filter(documents_total=0)


class ClientFilter(filters.FilterSet):
    q = filters.CharFilter(method="filter_q")
    client_type = filters.ChoiceFilter(choices=Client.ClientType.choices)
    document_type = filters.ChoiceFilter(choices=Client.IdentificationType.choices)

    class Meta:
        model = Client
        fields: list[str] = []

    def filter_q(self, queryset, name, value):
        term = (value or "").strip()
        if not term:
            return queryset
        condition = Q(name__icontains=term) | Q(email__icontains=term)
        queryset = queryset.annotate(name_fts=SearchVector("name", config=FTS_CONFIG))
        condition |= Q(name_fts=SearchQuery(term, config=FTS_CONFIG, search_type="plain"))
        digits = normalize_digits(term)
        if len(digits) >= 4:
            queryset = annotate_client_identification(queryset, "identification_number")
            condition |= Q(client_id_normalized__icontains=digits)
        return queryset.filter(condition).distinct()
