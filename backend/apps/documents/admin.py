from django.contrib import admin

from .models import Document, DocumentType, FilingSequence


@admin.register(FilingSequence)
class FilingSequenceAdmin(admin.ModelAdmin):
    list_display = ("date", "last_number")
    ordering = ("-date",)
    readonly_fields = ("date", "last_number")


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "category", "requires_expiration")
    list_filter = ("category", "requires_expiration")
    search_fields = ("name", "code")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        "filing_number",
        "original_filename",
        "processing_status",
        "source_channel",
        "created_at",
    )
    list_filter = ("processing_status", "source_channel")
    search_fields = ("filing_number", "original_filename")
    readonly_fields = ("filing_number", "created_at", "updated_at")
    ordering = ("-created_at",)
