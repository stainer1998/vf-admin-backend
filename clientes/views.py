from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Client
from .serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    serializer_class = ClientSerializer
    filterset_fields = ["type", "source"]
    search_fields = ["first_name", "last_name", "company_name", "rut", "phone", "email"]
    ordering_fields = ["first_name", "last_name", "company_name", "created_at"]
    ordering = ["-created_at"]

    def get_queryset(self):
        if self.request.query_params.get("deleted") == "true":
            return Client.all_objects.filter(deleted_at__isnull=False).select_related("merged_into")
        return Client.objects.select_related("merged_into")

    def destroy(self, request, *args, **kwargs):
        self.get_object().delete()
        return Response(status=204)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        client = Client.all_objects.get(pk=pk)
        client.restore()
        return Response(ClientSerializer(client).data)

    @action(detail=True, methods=["delete"], url_path="hard-delete")
    def hard_delete(self, request, pk=None):
        from django.db.models import ProtectedError

        password = request.data.get("password", "")
        if not request.user.check_password(password):
            return Response({"password": "Contraseña incorrecta."}, status=400)
        try:
            Client.all_objects.filter(pk=pk).delete()
        except ProtectedError:
            return Response(
                {"detail": "No se puede eliminar: el cliente tiene equipos, cotizaciones u órdenes de trabajo asociadas."},
                status=409,
            )
        return Response(status=204)
