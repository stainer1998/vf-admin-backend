from pydantic import ValidationError
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Diagnosis, ManualCorrection, StorageDevice
from .serializers import (
    DiagnosisListSerializer,
    DiagnosisSerializer,
    ManualCorrectionSerializer,
    StorageDeviceSerializer,
)
from .services import import_lookout_json


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

    @action(detail=False, methods=["post"], url_path="import")
    def import_lookout(self, request):
        data = request.data
        if not isinstance(data, dict):
            return Response({"detail": "Se esperaba un objeto JSON."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            diagnosis, created = import_lookout_json(data, request.user)
        except ValidationError as exc:
            return Response({"detail": "JSON inválido.", "errors": exc.errors()}, status=status.HTTP_400_BAD_REQUEST)
        serializer = DiagnosisSerializer(diagnosis)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

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
