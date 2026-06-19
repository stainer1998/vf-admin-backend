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

    @action(detail=True, methods=["delete"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        from django.db.models import ProtectedError

        password = request.data.get("password", "")
        if not request.user.check_password(password):
            return Response({"password": "Contraseña incorrecta."}, status=400)
        try:
            Equipment.all_objects.filter(pk=pk).delete()
        except ProtectedError:
            return Response(
                {"detail": "No se puede eliminar: el equipo tiene órdenes de trabajo o cotizaciones asociadas."},
                status=409,
            )
        return Response(status=204)
