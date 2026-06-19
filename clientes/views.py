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
