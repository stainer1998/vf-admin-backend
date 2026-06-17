from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from cotizaciones.models import Quote
from .models import WorkOrder, WorkOrderLine
from .serializers import WorkOrderListSerializer, WorkOrderLineSerializer, WorkOrderSerializer


class WorkOrderViewSet(viewsets.ModelViewSet):
    queryset = WorkOrder.objects.select_related(
        "client", "equipment", "source_quote"
    ).prefetch_related("lines").all()
    filterset_fields = ["client", "equipment", "work_status", "payment_status"]
    search_fields = ["number", "work_description", "notes"]
    ordering_fields = ["intake_date", "delivery_date", "number"]
    ordering = ["-intake_date"]

    def get_serializer_class(self):
        if self.action == "list":
            return WorkOrderListSerializer
        return WorkOrderSerializer

    @action(detail=False, methods=["post"], url_path="from-quote/(?P<quote_id>[^/.]+)")
    def from_quote(self, request, quote_id=None):
        """Create a work order by copying lines from an approved quote."""
        quote = Quote.objects.prefetch_related("lines").get(pk=quote_id)
        data = request.data.copy()
        data.setdefault("source_quote", quote.pk)
        data.setdefault("client", quote.client_id)
        data.setdefault("equipment", quote.equipment_id)

        lines = [
            {
                "line_type": line.line_type,
                "service": line.service_id,
                "product": line.product_id,
                "description": line.description,
                "unit_price": str(line.unit_price),
                "unit_cost": str(line.unit_cost),
                "quantity": line.quantity,
            }
            for line in quote.lines.all()
        ]
        data["lines"] = lines

        serializer = WorkOrderSerializer(data=data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=201)
