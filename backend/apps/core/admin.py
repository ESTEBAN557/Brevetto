from django.contrib import admin

from .models import Client, Contract, DigitalRecord, DocumentType


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("identification_number", "name", "document_type", "client_type", "email")
    search_fields = ("identification_number", "name", "email")
    list_filter = ("client_type", "document_type")


class DigitalRecordInline(admin.StackedInline):
    model = DigitalRecord
    extra = 0
    readonly_fields = ("storage_path", "created_at")


@admin.register(Contract)
class ContractAdmin(admin.ModelAdmin):
    list_display = ("contract_number", "client", "status", "start_date", "end_date")
    search_fields = ("contract_number", "client__name", "client__identification_number")
    list_filter = ("status",)
    autocomplete_fields = ("client",)
    inlines = [DigitalRecordInline]


@admin.register(DigitalRecord)
class DigitalRecordAdmin(admin.ModelAdmin):
    list_display = ("contract", "storage_path", "created_at")
    search_fields = ("contract__contract_number",)


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "category", "requires_expiration")
    list_filter = ("category", "requires_expiration")
    search_fields = ("code", "name")
