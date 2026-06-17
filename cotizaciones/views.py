from rest_framework import viewsets

from .models import Quote
from .serializers import QuoteListSerializer, QuoteSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client", "equipment").prefetch_related("lines").all()
    filterset_fields = ["client", "equipment", "status"]
    search_fields = ["folio", "notes"]
    ordering_fields = ["date", "folio", "status"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action == "list":
            return QuoteListSerializer
        return QuoteSerializer
