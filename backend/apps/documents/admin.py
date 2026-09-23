from django.contrib import admin

from .models import Document, FilingSequence


@admin.register(FilingSequence)
class FilingSequenceAdmin(admin.ModelAdmin):
    list_display = ("date", "last_number")
    ordering = ("-date",)
    readonly_fields = ("date", "last_number")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("filing_number", "original_filename", "processing_status", "created_at")
    list_filter = ("processing_status", "mime_type")
    search_fields = ("filing_number", "original_filename")
    readonly_fields = ("filing_number", "created_at", "updated_at")
