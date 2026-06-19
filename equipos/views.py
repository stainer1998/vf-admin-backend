from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Equipment
from .serializers import EquipmentSerializer


class EquipmentViewSet(viewsets.ModelViewSet):
    serializer_class = EquipmentSerializer
    filterset_fields = ["client", "type", "desktop_subtype", "is_ambiguous"]
    search_fields = ["brand", "model", "serial_number"]
    ordering_fields = ["brand", "model", "year", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if self.request.query_params.get("deleted") == "true":
            return Equipment.all_objects.filter(deleted_at__isnull=False).select_related("client")
        return Equipment.objects.select_related("client")

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        equipment = Equipment.all_objects.get(pk=pk)
        equipment.restore()
        return Response(EquipmentSerializer(equipment).data)
