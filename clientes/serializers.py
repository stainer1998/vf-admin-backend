from rest_framework import serializers

from .models import Client


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "type",
            "first_name",
            "last_name",
            "second_last_name",
            "identity_key",
            "phone",
            "email",
            "rut",
            "company_name",
            "address",
            "notes",
            "merged_into",
            "source",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["identity_key", "created_at", "updated_at"]
