from rest_framework import serializers

from .models import Equipment


class EquipmentSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.__str__", read_only=True)

    class Meta:
        model = Equipment
        fields = [
            "id",
            "client",
            "client_name",
            "type",
            "desktop_subtype",
            "brand",
            "model",
            "serial_number",
            "year",
            "identity_key",
            "is_ambiguous",
            "created_at",
            "updated_at",
            "deleted_at",
        ]
        read_only_fields = ["identity_key", "is_ambiguous", "created_at", "updated_at", "deleted_at"]
