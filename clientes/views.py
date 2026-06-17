from rest_framework import viewsets

from .models import Client
from .serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.select_related("merged_into").all()
    serializer_class = ClientSerializer
    filterset_fields = ["type", "source"]
    search_fields = ["first_name", "last_name", "company_name", "rut", "phone", "email"]
    ordering_fields = ["first_name", "last_name", "company_name", "created_at"]
    ordering = ["-created_at"]
