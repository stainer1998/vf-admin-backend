from rest_framework import serializers

from .models import Service, ServiceMaterial, ServiceRequiredCategory


class ServiceMaterialSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    product_code = serializers.CharField(source="product.code", read_only=True)
    sale_price = serializers.DecimalField(
        source="product.sale_price", max_digits=12, decimal_places=2, read_only=True
    )
    purchase_price = serializers.DecimalField(
        source="product.purchase_price", max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = ServiceMaterial
        fields = [
            "id",
            "product",
            "product_name",
            "product_code",
            "sale_price",
            "purchase_price",
            "default_quantity",
        ]


class ServiceRequiredCategorySerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = ServiceRequiredCategory
        fields = ["id", "category", "category_name", "label", "billable", "default_quantity"]


class ServiceSerializer(serializers.ModelSerializer):
    gross_profit = serializers.SerializerMethodField()
    margin = serializers.SerializerMethodField()
    materials = ServiceMaterialSerializer(many=True, required=False)
    required_categories = ServiceRequiredCategorySerializer(many=True, required=False)

    class Meta:
        model = Service
        fields = [
            "id",
            "code",
            "name",
            "description",
            "sale_price",
            "direct_cost",
            "gross_profit",
            "margin",
            "is_active",
            "notes",
            "materials",
            "required_categories",
        ]

    def get_gross_profit(self, obj):
        return obj.gross_profit

    def get_margin(self, obj):
        return obj.margin

    def _save_materials(self, service, materials_data):
        existing = {m.product_id: m for m in service.materials.all()}
        incoming_ids = set()

        for item in materials_data:
            product = item["product"]
            qty = item.get("default_quantity", 1)
            incoming_ids.add(product.id)
            if product.id in existing:
                mat = existing[product.id]
                if mat.default_quantity != qty:
                    mat.default_quantity = qty
                    mat.save()
            else:
                ServiceMaterial.objects.create(
                    service=service, product=product, default_quantity=qty
                )

        # Remove materials not in the incoming set
        service.materials.filter(product_id__in=(set(existing) - incoming_ids)).delete()

    def _save_required_categories(self, service, categories_data):
        service.required_categories.all().delete()
        for item in categories_data:
            ServiceRequiredCategory.objects.create(
                service=service,
                category=item["category"],
                label=item.get("label", ""),
                billable=item.get("billable", True),
                default_quantity=item.get("default_quantity", 1),
            )

    def create(self, validated_data):
        materials_data = validated_data.pop("materials", [])
        categories_data = validated_data.pop("required_categories", [])
        service = super().create(validated_data)
        self._save_materials(service, materials_data)
        self._save_required_categories(service, categories_data)
        return service

    def update(self, instance, validated_data):
        materials_data = validated_data.pop("materials", None)
        categories_data = validated_data.pop("required_categories", None)
        service = super().update(instance, validated_data)
        if materials_data is not None:
            self._save_materials(service, materials_data)
        if categories_data is not None:
            self._save_required_categories(service, categories_data)
        return service
