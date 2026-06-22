from decimal import Decimal

from rest_framework import serializers

from .models import Quote, QuoteLine


class QuoteLineSerializer(serializers.ModelSerializer):
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = QuoteLine
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


class QuoteSerializer(serializers.ModelSerializer):
    lines = QuoteLineSerializer(many=True, required=False)
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()
    client_name = serializers.CharField(source="client.__str__", read_only=True)
    work_order_id = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "folio",
            "client",
            "client_name",
            "equipment",
            "source_diagnosis",
            "date",
            "validity_days",
            "status",
            "iva",
            "notes",
            "subtotal",
            "total",
            "lines",
            "work_order_id",
        ]
        read_only_fields = ["folio"]

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_total(self, obj):
        return obj.total

    def get_work_order_id(self, obj):
        wo = obj.work_orders.first()
        return wo.pk if wo else None

    def create(self, validated_data):
        lines_data = validated_data.pop("lines", [])
        quote = Quote.objects.create(**validated_data)
        for line_data in lines_data:
            QuoteLine.objects.create(quote=quote, **line_data)
        return quote

    def update(self, instance, validated_data):
        lines_data = validated_data.pop("lines", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if lines_data is not None:
            instance.lines.all().delete()
            for line_data in lines_data:
                QuoteLine.objects.create(quote=instance, **line_data)
        return instance


class QuoteListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits nested lines."""

    client_name = serializers.CharField(source="client.__str__", read_only=True)
    subtotal = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Quote
        fields = [
            "id",
            "folio",
            "client",
            "client_name",
            "equipment",
            "date",
            "status",
            "subtotal",
            "total",
        ]

    def get_subtotal(self, obj):
        return obj.subtotal

    def get_total(self, obj):
        return obj.total
