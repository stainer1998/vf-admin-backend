from django.contrib import admin

from .models import InventoryMovement, Product, ProductCategory, Supplier


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "is_stockable", "description"]
    list_filter = ["is_stockable"]
    search_fields = ["name"]


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ["name", "notes"]
    search_fields = ["name"]


class InventoryMovementInline(admin.TabularInline):
    model = InventoryMovement
    extra = 0
    fields = ["movement_type", "quantity", "unit_cost", "date", "reference"]
    ordering = ["-date"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        "code", "name", "category", "purchase_price", "sale_price",
        "margin_display", "stock_display",
    ]
    list_filter = ["category", "supplier"]
    search_fields = ["code", "name"]
    readonly_fields = ["margin_display", "stock_display"]
    inlines = [InventoryMovementInline]

    @admin.display(description="Margin %")
    def margin_display(self, obj):
        return f"{obj.margin}%"

    @admin.display(description="Stock")
    def stock_display(self, obj):
        return obj.stock


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ["product", "movement_type", "quantity", "unit_cost", "date", "reference"]
    list_filter = ["movement_type"]
    search_fields = ["product__name", "product__code", "reference"]
    date_hierarchy = "date"
    autocomplete_fields = ["product"]
