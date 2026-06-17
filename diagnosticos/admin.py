from django.contrib import admin

from .models import Diagnosis, DetectedSpecification, ManualCorrection, StorageDevice


class DetectedSpecificationInline(admin.StackedInline):
    model = DetectedSpecification
    extra = 0
    can_delete = False


class StorageDeviceInline(admin.TabularInline):
    model = StorageDevice
    extra = 0
    fields = ["category", "disk_type", "interface", "capacity_gb", "raw_model"]


class ManualCorrectionInline(admin.TabularInline):
    model = ManualCorrection
    extra = 0
    readonly_fields = ["corrected_by", "corrected_at"]
    fields = ["field", "value", "corrected_by", "corrected_at"]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.corrected_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(Diagnosis)
class DiagnosisAdmin(admin.ModelAdmin):
    list_display = [
        "id", "equipment", "timestamp", "schema_version", "ingress_source", "imported_at",
    ]
    list_filter = ["ingress_source", "schema_version"]
    search_fields = ["content_hash", "source_file", "equipment__serial_number"]
    readonly_fields = ["content_hash", "imported_at", "imported_by"]
    autocomplete_fields = ["equipment"]
    inlines = [DetectedSpecificationInline, StorageDeviceInline, ManualCorrectionInline]
    fieldsets = [
        (None, {
            "fields": ["equipment", "ingress_source", "source_file", "schema_version", "timestamp"],
        }),
        ("Raw data", {
            "fields": ["raw_json"],
            "classes": ["collapse"],
        }),
        ("Import metadata", {
            "fields": ["content_hash", "imported_at", "imported_by"],
            "classes": ["collapse"],
        }),
    ]

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.imported_by = request.user
        super().save_model(request, obj, form, change)
