from django.contrib import admin

from .models import FilingSequence


@admin.register(FilingSequence)
class FilingSequenceAdmin(admin.ModelAdmin):
    list_display = ("date", "last_number")
    ordering = ("-date",)
    readonly_fields = ("date", "last_number")
