"""Administración de requerimientos: el personal asigna, responde y cambia el estado (con rastro)."""

from django.contrib import admin, messages

from apps.customer.models import (
    ClientAccount,
    ServiceRequest,
    ServiceRequestAttachment,
    ServiceRequestMessage,
)


class MessageInline(admin.TabularInline):
    model = ServiceRequestMessage
    extra = 1
    fields = ("author_type", "author_name", "body", "created_at")
    readonly_fields = ("created_at",)


class AttachmentInline(admin.TabularInline):
    model = ServiceRequestAttachment
    extra = 0
    fields = ("original_filename", "from_client", "file_size_bytes", "created_at")
    readonly_fields = fields
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "subject", "client", "contract", "status", "assigned_to", "created_at")
    list_filter = ("status", "service")
    search_fields = ("id", "subject", "client__name", "contract__contract_number")
    readonly_fields = ("client", "contract", "case_type", "service", "subcategory", "subject", "description")
    inlines = (MessageInline, AttachmentInline)
    actions = ("mark_assigned", "mark_in_progress", "mark_resolved", "mark_closed")

    def save_model(self, request, obj, form, change):
        previous = ServiceRequest.objects.filter(pk=obj.pk).values_list("status", flat=True).first()
        super().save_model(request, obj, form, change)
        if change and previous and previous != obj.status:
            obj.change_status(obj.status, actor=request.user.get_full_name() or request.user.username)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, ServiceRequestMessage) and not instance.author_name:
                instance.author_name = request.user.get_full_name() or request.user.username
            instance.save()
        formset.save_m2m()

    def _set_status(self, request, queryset, status):
        actor = request.user.get_full_name() or request.user.username
        for obj in queryset:
            if obj.status != status:
                obj.change_status(status, actor=actor)
        self.message_user(request, f"{queryset.count()} requerimiento(s) actualizado(s).", messages.SUCCESS)

    @admin.action(description="Marcar como Asignado")
    def mark_assigned(self, request, queryset):
        self._set_status(request, queryset, ServiceRequest.Status.ASSIGNED)

    @admin.action(description="Marcar como En proceso")
    def mark_in_progress(self, request, queryset):
        self._set_status(request, queryset, ServiceRequest.Status.IN_PROGRESS)

    @admin.action(description="Marcar como Resuelto")
    def mark_resolved(self, request, queryset):
        self._set_status(request, queryset, ServiceRequest.Status.RESOLVED)

    @admin.action(description="Marcar como Cerrado")
    def mark_closed(self, request, queryset):
        self._set_status(request, queryset, ServiceRequest.Status.CLOSED)


@admin.register(ClientAccount)
class ClientAccountAdmin(admin.ModelAdmin):
    list_display = ("email", "client", "last_login_at")
    search_fields = ("email", "client__name")
    readonly_fields = ("password_hash", "last_login_at")
