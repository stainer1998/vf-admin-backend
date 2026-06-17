from rest_framework import viewsets

from .models import Equipment
from .serializers import EquipmentSerializer


class EquipmentViewSet(viewsets.ModelViewSet):
    queryset = Equipment.objects.select_related("client").all()
    serializer_class = EquipmentSerializer
    filterset_fields = ["client", "type", "desktop_subtype", "is_ambiguous"]
    search_fields = ["brand", "model", "serial_number"]
    ordering_fields = ["brand", "model", "year", "created_at"]
    ordering = ["-created_at"]
