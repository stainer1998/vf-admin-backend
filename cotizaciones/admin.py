from django.contrib import admin

from .models import Quote, QuoteLine


class QuoteLineInline(admin.TabularInline):
    model = QuoteLine
    extra = 1
    fields = [
        "line_type", "service", "product",
        "description", "unit_price", "unit_cost", "quantity", "subtotal_display",
    ]
    readonly_fields = ["subtotal_display"]

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return obj.subtotal if obj.pk else "—"


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = [
        "folio", "client", "equipment", "date", "validity_days",
        "status", "subtotal_display", "total_display",
    ]
    list_filter = ["status"]
    search_fields = ["folio", "notes", "client__first_name", "client__company_name"]
    readonly_fields = ["folio", "subtotal_display", "total_display"]
    autocomplete_fields = ["client", "equipment"]
    inlines = [QuoteLineInline]
    fieldsets = [
        (None, {
            "fields": ["folio", "client", "equipment", "source_diagnosis"],
        }),
        ("Details", {
            "fields": ["date", "validity_days", "status", "iva", "notes"],
        }),
        ("Totals", {
            "fields": ["subtotal_display", "total_display"],
        }),
    ]

    @admin.display(description="Subtotal")
    def subtotal_display(self, obj):
        return obj.subtotal

    @admin.display(description="Total")
    def total_display(self, obj):
        return obj.total
