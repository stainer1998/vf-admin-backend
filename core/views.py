from rest_framework import viewsets
from rest_framework.generics import RetrieveUpdateAPIView

from .models import AllocationFund, DiskInterpretation, EquipmentLevel, EmpresaConfig
from .serializers import (
    AllocationFundSerializer,
    DiskInterpretationSerializer,
    EquipmentLevelSerializer,
    EmpresaConfigSerializer,
)


class AllocationFundViewSet(viewsets.ModelViewSet):
    queryset = AllocationFund.objects.all()
    serializer_class = AllocationFundSerializer
    ordering_fields = ["order", "name", "percentage"]


class DiskInterpretationViewSet(viewsets.ModelViewSet):
    queryset = DiskInterpretation.objects.all()
    serializer_class = DiskInterpretationSerializer
    search_fields = ["pattern", "manufacturer"]
    filterset_fields = ["disk_type"]


class EquipmentLevelViewSet(viewsets.ModelViewSet):
    queryset = EquipmentLevel.objects.all()
    serializer_class = EquipmentLevelSerializer
    ordering_fields = ["order", "name"]


class EmpresaConfigView(RetrieveUpdateAPIView):
    serializer_class = EmpresaConfigSerializer

    def get_object(self):
        return EmpresaConfig.get_instance()
