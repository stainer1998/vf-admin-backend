from rest_framework import serializers

from .models import InventoryMovement, Product, ProductCategory, Supplier


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "code_prefix", "is_stockable", "description"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "notes"]


class ProductSerializer(serializers.ModelSerializer):
    margin = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_name",
            "purchase_price",
            "sale_price",
            "margin",
            "stock",
            "supplier",
            "supplier_name",
            "notes",
        ]

    def get_margin(self, obj):
        return obj.margin

    def get_stock(self, obj):
        return obj.stock


class InventoryMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = InventoryMovement
        fields = [
            "id",
            "product",
            "product_name",
            "movement_type",
            "quantity",
            "unit_cost",
            "date",
            "reference",
            "notes",
        ]
