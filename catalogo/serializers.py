from rest_framework import serializers

from .models import Service


class ServiceSerializer(serializers.ModelSerializer):
    gross_profit = serializers.SerializerMethodField()
    margin = serializers.SerializerMethodField()

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
        ]

    def get_gross_profit(self, obj):
        return obj.gross_profit

    def get_margin(self, obj):
        return obj.margin
