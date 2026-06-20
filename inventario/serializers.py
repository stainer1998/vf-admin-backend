from rest_framework import serializers

from .models import Brand, InventoryMovement, Product, ProductCategory, ProductSupplier, Supplier


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "code_prefix", "is_stockable", "description"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "notes"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "name"]


class ProductSupplierSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source="supplier.id")
    name = serializers.CharField(source="supplier.name")

    class Meta:
        model = ProductSupplier
        fields = ["id", "name", "purchase_price", "is_preferred"]


class ProductSupplierWriteSerializer(serializers.Serializer):
    supplier = serializers.PrimaryKeyRelatedField(queryset=Supplier.objects.all())
    purchase_price = serializers.DecimalField(
        max_digits=10, decimal_places=2, required=False, allow_null=True
    )
    is_preferred = serializers.BooleanField(default=False)
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class ProductSerializer(serializers.ModelSerializer):
    margin = serializers.SerializerMethodField()
    stock = serializers.SerializerMethodField()
    category_name = serializers.CharField(source="category.name", read_only=True)
    brand_name = serializers.CharField(source="brand.name", read_only=True, default="")
    suppliers = ProductSupplierSerializer(
        source="product_suppliers", many=True, read_only=True
    )
    suppliers_write = ProductSupplierWriteSerializer(
        many=True, write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "code",
            "name",
            "category",
            "category_name",
            "brand",
            "brand_name",
            "model",
            "purchase_price",
            "sale_price",
            "margin",
            "stock",
            "suppliers",
            "suppliers_write",
            "notes",
        ]

    def get_margin(self, obj):
        return obj.margin

    def get_stock(self, obj):
        return obj.stock

    def create(self, validated_data):
        suppliers_data = validated_data.pop("suppliers_write", [])
        product = super().create(validated_data)
        self._save_suppliers(product, suppliers_data)
        return product

    def update(self, instance, validated_data):
        suppliers_data = validated_data.pop("suppliers_write", None)
        product = super().update(instance, validated_data)
        if suppliers_data is not None:
            self._save_suppliers(product, suppliers_data)
        return product

    def _save_suppliers(self, product, suppliers_data):
        product.product_suppliers.all().delete()
        for item in suppliers_data:
            ProductSupplier.objects.create(
                product=product,
                supplier=item["supplier"],
                purchase_price=item.get("purchase_price"),
                is_preferred=item.get("is_preferred", False),
                notes=item.get("notes", ""),
            )


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
