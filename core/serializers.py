from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import AllocationFund, DiskInterpretation, EquipmentLevel, EmpresaConfig


class AllocationFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllocationFund
        fields = ["id", "name", "slug", "description", "color", "order", "is_active", "percentage"]

    def validate(self, attrs):
        fields = ["name", "slug", "description", "color", "order", "is_active", "percentage"]
        merged = {f: getattr(self.instance, f) for f in fields} if self.instance else {}
        merged.update(attrs)
        instance = AllocationFund(pk=self.instance.pk if self.instance else None, **merged)
        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict if hasattr(exc, "message_dict") else exc.messages)
        return attrs


class DiskInterpretationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiskInterpretation
        fields = ["id", "pattern", "manufacturer", "capacity", "rpm", "disk_type"]


class EquipmentLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentLevel
        fields = ["id", "name", "description", "order"]


class EmpresaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmpresaConfig
        fields = ["nombre", "slogan", "email", "telefono", "direccion", "sitio_web"]
