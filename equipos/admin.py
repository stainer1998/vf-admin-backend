from django.contrib import admin

from .models import Equipment


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        "id", "__str__", "client", "type", "serial_number", "year", "is_ambiguous",
    ]
    list_filter = ["type", "desktop_subtype", "is_ambiguous"]
    search_fields = ["brand", "model", "serial_number", "client__first_name", "client__company_name"]
    readonly_fields = ["identity_key", "is_ambiguous", "created_at", "updated_at"]
    autocomplete_fields = ["client"]
    fieldsets = [
        (None, {
            "fields": ["client", "type", "desktop_subtype"],
        }),
        ("Hardware", {
            "fields": ["brand", "model", "serial_number", "year"],
        }),
        ("Identity", {
            "fields": ["identity_key", "is_ambiguous"],
            "classes": ["collapse"],
        }),
        ("Timestamps", {
            "fields": ["created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
