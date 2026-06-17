from rest_framework import serializers

from .models import AllocationFund, DiskInterpretation, EquipmentLevel


class AllocationFundSerializer(serializers.ModelSerializer):
    class Meta:
        model = AllocationFund
        fields = ["id", "name", "slug", "description", "color", "order", "is_active", "percentage"]


class DiskInterpretationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiskInterpretation
        fields = ["id", "pattern", "manufacturer", "capacity", "rpm", "disk_type"]


class EquipmentLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = EquipmentLevel
        fields = ["id", "name", "description", "order"]
