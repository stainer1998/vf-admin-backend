from rest_framework import serializers

from .models import (
    Brand, InventoryMovement, Product, ProductCategory,
    ProductSupplier, PurchaseOrder, PurchaseOrderLine, Supplier,
)


class ProductCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductCategory
        fields = ["id", "name", "code_prefix", "is_stockable", "is_equipment_component", "description", "spec_schema"]


class SupplierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplier
        fields = ["id", "name", "phone", "website", "address", "comuna", "city", "notes"]


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
        max_digits=12, decimal_places=2, required=False, allow_null=True
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
            "specifications",
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


class PurchaseOrderLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    pending_quantity = serializers.SerializerMethodField()
    is_fully_received = serializers.SerializerMethodField()
    total_ordered = serializers.SerializerMethodField()
    total_received = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrderLine
        fields = [
            "id",
            "product",
            "product_name",
            "description",
            "unit_cost",
            "quantity_ordered",
            "quantity_received",
            "pending_quantity",
            "is_fully_received",
            "total_ordered",
            "total_received",
        ]

    def get_pending_quantity(self, obj):
        return obj.pending_quantity

    def get_is_fully_received(self, obj):
        return obj.is_fully_received

    def get_total_ordered(self, obj):
        return str(obj.total_ordered)

    def get_total_received(self, obj):
        return str(obj.total_received)


class PurchaseOrderListSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    total_lines = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    received_lines = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "number",
            "supplier",
            "supplier_name",
            "date",
            "expected_date",
            "status",
            "total_lines",
            "received_lines",
            "total_cost",
            "created_at",
        ]

    def get_total_lines(self, obj):
        return obj.lines.count()

    def get_received_lines(self, obj):
        return sum(1 for l in obj.lines.all() if l.is_fully_received)

    def get_total_cost(self, obj):
        total = sum(l.total_ordered for l in obj.lines.all())
        return str(total)


class PurchaseOrderSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True)
    lines = PurchaseOrderLineSerializer(many=True)
    total_cost = serializers.SerializerMethodField()

    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "number",
            "supplier",
            "supplier_name",
            "date",
            "expected_date",
            "status",
            "notes",
            "lines",
            "total_cost",
            "created_at",
        ]
        read_only_fields = ["number", "status"]

    def get_total_cost(self, obj):
        total = sum(l.total_ordered for l in obj.lines.all())
        return str(total)

    def validate_lines(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos una línea.")
        return value

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        po = PurchaseOrder.objects.create(**validated_data)
        for line in lines_data:
            PurchaseOrderLine.objects.create(purchase_order=po, **line)
        return po

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line in lines_data:
                PurchaseOrderLine.objects.create(purchase_order=instance, **line)
        return instance
