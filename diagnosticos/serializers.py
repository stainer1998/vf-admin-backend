from rest_framework import serializers

from .models import Diagnosis, DetectedSpecification, ManualCorrection, StorageDevice


class DetectedSpecificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectedSpecification
        fields = [
            "id",
            "os_name",
            "os_version",
            "cpu_model",
            "ram_total_gb",
            "gpu_model",
        ]


class StorageDeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageDevice
        fields = [
            "id",
            "category",
            "disk_type",
            "interface",
            "capacity_gb",
            "raw_model",
        ]


class ManualCorrectionSerializer(serializers.ModelSerializer):
    corrected_by_username = serializers.CharField(
        source="corrected_by.username", read_only=True
    )

    class Meta:
        model = ManualCorrection
        fields = [
            "id",
            "field",
            "value",
            "corrected_by",
            "corrected_by_username",
            "corrected_at",
        ]
        read_only_fields = ["corrected_by", "corrected_at"]


class DiagnosisSerializer(serializers.ModelSerializer):
    specification = DetectedSpecificationSerializer(read_only=True)
    storage_devices = StorageDeviceSerializer(many=True, read_only=True)
    corrections = ManualCorrectionSerializer(many=True, read_only=True)
    imported_by_username = serializers.CharField(
        source="imported_by.username", read_only=True
    )

    class Meta:
        model = Diagnosis
        fields = [
            "id",
            "equipment",
            "timestamp",
            "source_file",
            "schema_version",
            "raw_json",
            "ingress_source",
            "content_hash",
            "imported_at",
            "imported_by",
            "imported_by_username",
            "specification",
            "storage_devices",
            "corrections",
        ]
        read_only_fields = ["content_hash", "imported_at", "imported_by"]


class DiagnosisListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits raw_json and nested data."""

    class Meta:
        model = Diagnosis
        fields = [
            "id",
            "equipment",
            "timestamp",
            "schema_version",
            "ingress_source",
            "content_hash",
            "imported_at",
        ]
