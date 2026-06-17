from django.contrib import admin

from .models import AllocationFund, DiskInterpretation, EquipmentLevel


@admin.register(AllocationFund)
class AllocationFundAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "percentage", "is_active", "order", "color"]
    list_filter = ["is_active"]
    list_editable = ["percentage", "order", "is_active"]
    search_fields = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(DiskInterpretation)
class DiskInterpretationAdmin(admin.ModelAdmin):
    list_display = ["pattern", "manufacturer", "capacity", "disk_type", "rpm"]
    list_filter = ["disk_type"]
    search_fields = ["pattern", "manufacturer"]


@admin.register(EquipmentLevel)
class EquipmentLevelAdmin(admin.ModelAdmin):
    list_display = ["name", "order", "description"]
    list_editable = ["order"]
