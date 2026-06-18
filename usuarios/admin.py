from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import UsuarioVF


@admin.register(UsuarioVF)
class UsuarioVFAdmin(UserAdmin):
    list_display  = ["username", "email", "first_name", "last_name", "rol", "is_staff", "is_active"]
    list_filter   = ["rol", "is_staff", "is_active", "is_superuser"]
    fieldsets     = UserAdmin.fieldsets + (
        ("Rol VF", {"fields": ("rol",)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Rol VF", {"fields": ("rol",)}),
    )
