from django.contrib import admin

from .models import Service


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "sale_price", "direct_cost", "gross_profit_display",
        "margin_display", "is_active",
    ]
    list_filter = ["is_active"]
    search_fields = ["code", "name", "description"]
    readonly_fields = ["gross_profit_display", "margin_display"]

    @admin.display(description="Gross profit")
    def gross_profit_display(self, obj):
        return obj.gross_profit

    @admin.display(description="Margin %")
    def margin_display(self, obj):
        return f"{obj.margin}%"
