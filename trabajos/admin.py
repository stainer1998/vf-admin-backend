from django.contrib import admin

from .models import WorkOrder, WorkOrderLine


class WorkOrderLineInline(admin.TabularInline):
    model = WorkOrderLine
    extra = 1
    fields = [
        "line_type", "service", "product",
        "description", "unit_price", "unit_cost", "quantity", "subtotal_display",
    ]
    readonly_fields = ["subtotal_display"]

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return obj.subtotal if obj.pk else "—"


@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = [
        "number", "client", "equipment", "intake_date", "delivery_date",
        "work_status", "payment_status", "amount_charged_display",
    ]
    list_filter = ["work_status", "payment_status", "payment_method"]
    search_fields = ["number", "work_description", "client__first_name", "client__company_name"]
    readonly_fields = ["number", "amount_charged_display"]
    autocomplete_fields = ["client", "equipment", "source_quote"]
    date_hierarchy = "intake_date"
    inlines = [WorkOrderLineInline]
    fieldsets = [
        (None, {
            "fields": ["number", "client", "equipment", "source_quote"],
        }),
        ("Status", {
            "fields": [
                "work_status", "intake_date", "delivery_date",
                "payment_status", "payment_method",
            ],
        }),
        ("Details", {
            "fields": ["work_description", "notes", "adjustment"],
        }),
        ("Total", {
            "fields": ["amount_charged_display"],
        }),
    ]

    @admin.display(description="Amount charged")
    def amount_charged_display(self, obj):
        return obj.amount_charged
