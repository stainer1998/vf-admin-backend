from datetime import date

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Quote
from .serializers import QuoteListSerializer, QuoteSerializer


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related("client", "equipment").prefetch_related("lines", "work_orders").all()
    filterset_fields = ["client", "equipment", "status"]
    search_fields = ["folio", "notes"]
    ordering_fields = ["date", "folio", "status"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action == "list":
            return QuoteListSerializer
        return QuoteSerializer

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Mark quote as APPROVED and create a WorkOrder from its lines atomically."""
        from trabajos.models import WorkOrder, WorkOrderLine
        from trabajos.serializers import WorkOrderSerializer

        quote = self.get_object()

        if quote.status not in (Quote.DRAFT, Quote.SENT):
            return Response(
                {"detail": "Solo se pueden aprobar cotizaciones en estado Borrador o Enviada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not quote.equipment_id:
            return Response(
                {"detail": "La cotización debe tener un equipo asociado para crear una OT."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        intake_date_raw = request.data.get("intake_date") or date.today().isoformat()

        with transaction.atomic():
            quote.status = Quote.APPROVED
            quote.save(update_fields=["status"])

            wo = WorkOrder.objects.create(
                client=quote.client,
                equipment=quote.equipment,
                source_quote=quote,
                intake_date=intake_date_raw,
                work_description=quote.notes,
                notes=f"Generada desde {quote.folio} · Total cotizado: ${quote.total:,.0f}",
            )
            WorkOrderLine.objects.bulk_create([
                WorkOrderLine(
                    work_order=wo,
                    line_type=line.line_type,
                    service=line.service,
                    product=line.product,
                    description=line.description,
                    unit_price=line.unit_price,
                    unit_cost=line.unit_cost,
                    quantity=line.quantity,
                )
                for line in quote.lines.all()
            ])

        return Response(
            WorkOrderSerializer(wo, context={"request": request}).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Mark quote as REJECTED."""
        quote = self.get_object()

        if quote.status not in (Quote.DRAFT, Quote.SENT):
            return Response(
                {"detail": "Solo se pueden rechazar cotizaciones en estado Borrador o Enviada."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        quote.status = Quote.REJECTED
        quote.save(update_fields=["status"])

        return Response(QuoteSerializer(quote, context={"request": request}).data)
