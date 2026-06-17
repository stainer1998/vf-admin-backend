from rest_framework import viewsets

from .models import Service
from .serializers import ServiceSerializer


class ServiceViewSet(viewsets.ModelViewSet):
    queryset = Service.objects.all()
    serializer_class = ServiceSerializer
    filterset_fields = ["is_active"]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "sale_price"]
    ordering = ["code"]
