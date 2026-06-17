from django.contrib import admin

from .models import Client


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = [
        "id", "__str__", "type", "phone", "email", "rut", "source", "created_at",
    ]
    list_filter = ["type", "source"]
    search_fields = ["first_name", "last_name", "company_name", "rut", "phone", "email"]
    readonly_fields = ["identity_key", "created_at", "updated_at"]
    fieldsets = [
        (None, {
            "fields": ["type", "source", "identity_key"],
        }),
        ("Name / Contact", {
            "fields": [
                "first_name", "last_name", "second_last_name",
                "phone", "email", "address",
            ],
        }),
        ("Company", {
            "fields": ["company_name", "rut"],
            "classes": ["collapse"],
        }),
        ("Extra", {
            "fields": ["notes", "merged_into", "created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]
