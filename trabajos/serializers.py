from rest_framework import serializers

from .models import WorkOrder, WorkOrderLine


class WorkOrderLineSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrderLine
        fields = [
            "id",
            "line_type",
            "service",
            "product",
            "description",
            "unit_price",
            "unit_cost",
            "quantity",
            "subtotal",
        ]

    def get_subtotal(self, obj):
        return obj.subtotal

    def validate(self, data):
        service = data.get("service")
        product = data.get("product")
        if bool(service) == bool(product):
            raise serializers.ValidationError(
                "Each line must have exactly one of: service or product."
            )
        return data


class WorkOrderSerializer(serializers.ModelSerializer):
    lines = WorkOrderLineSerializer(many=True, required=False)
    amount_charged = serializers.SerializerMethodField()
    client_name = serializers.CharField(source="client.__str__", read_only=True)
    equipment_label = serializers.CharField(source="equipment.__str__", read_only=True)

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "number",
            "client",
            "client_name",
            "equipment",
            "equipment_label",
            "source_quote",
            "intake_date",
            "delivery_date",
            "work_status",
            "payment_status",
            "payment_method",
            "adjustment",
            "work_description",
            "notes",
            "amount_charged",
            "lines",
        ]
        read_only_fields = ["number"]

    def get_amount_charged(self, obj):
        return obj.amount_charged

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        work_order = WorkOrder.objects.create(**validated_data)
        for line_data in lines_data:
            WorkOrderLine.objects.create(work_order=work_order, **line_data)
        return work_order

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                WorkOrderLine.objects.create(work_order=instance, **line_data)
        return instance


class WorkOrderListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits nested lines."""

    client_name = serializers.CharField(source="client.__str__", read_only=True)
    amount_charged = serializers.SerializerMethodField()

    class Meta:
        model = WorkOrder
        fields = [
            "id",
            "number",
            "client",
            "client_name",
            "equipment",
            "intake_date",
            "delivery_date",
            "work_status",
            "payment_status",
            "amount_charged",
        ]

    def get_amount_charged(self, obj):
        return obj.amount_charged
