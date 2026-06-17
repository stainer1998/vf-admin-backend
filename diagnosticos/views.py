from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Diagnosis, ManualCorrection, StorageDevice
from .serializers import (
    DiagnosisListSerializer,
    DiagnosisSerializer,
    ManualCorrectionSerializer,
    StorageDeviceSerializer,
)


class DiagnosisViewSet(viewsets.ModelViewSet):
    queryset = Diagnosis.objects.select_related(
        "equipment", "imported_by", "specification"
    ).prefetch_related("storage_devices", "corrections").all()
    filterset_fields = ["equipment", "ingress_source", "schema_version"]
    search_fields = ["source_file", "content_hash"]
    ordering_fields = ["timestamp", "imported_at"]
    ordering = ["-timestamp"]

    def get_serializer_class(self):
        if self.action == "list":
            return DiagnosisListSerializer
        return DiagnosisSerializer

    def perform_create(self, serializer):
        serializer.save(imported_by=self.request.user)

    @action(detail=True, methods=["post"])
    def correct(self, request, pk=None):
        diagnosis = self.get_object()
        serializer = ManualCorrectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(diagnosis=diagnosis, corrected_by=request.user)
        return Response(serializer.data, status=201)


class StorageDeviceViewSet(viewsets.ModelViewSet):
    queryset = StorageDevice.objects.select_related("diagnosis").all()
    serializer_class = StorageDeviceSerializer
    filterset_fields = ["diagnosis", "category", "disk_type", "interface"]
