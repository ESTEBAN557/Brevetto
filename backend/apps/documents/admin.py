from django.contrib import admin

from .models import AuditLog, Document, FilingSequence


@admin.register(FilingSequence)
class FilingSequenceAdmin(admin.ModelAdmin):
    list_display = ("date", "last_number")
    readonly_fields = ("date", "last_number")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "filing_number",
        "original_filename",
        "processing_status",
        "source_channel",
        "document_type",
        "ai_confidence_score",
        "created_at",
    )
    list_filter = ("processing_status", "source_channel", "document_type")
    search_fields = ("filing_number", "original_filename", "file_hash", "external_sender_name")
    readonly_fields = ("filing_number", "file_hash", "file_size_bytes", "created_at", "updated_at")
    date_hierarchy = "created_at"


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Vista de solo lectura: la bitácora es inmutable."""

    list_display = ("timestamp", "action", "document", "performed_by", "ip_address")
    list_filter = ("action",)
    search_fields = ("document__filing_number", "performed_by__username")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
