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

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        from django.db.models import Count

        status_counts = dict(
            WorkOrder.objects.values_list("work_status")
            .annotate(n=Count("id"))
            .values_list("work_status", "n")
        )
        ready = (
            WorkOrder.objects.filter(work_status="READY")
            .select_related("client", "equipment")
            .order_by("intake_date")[:10]
        )
        pending = (
            WorkOrder.objects.filter(payment_status="PENDING")
            .exclude(work_status="DELIVERED")
            .select_related("client", "equipment")
            .order_by("intake_date")[:10]
        )
        return Response(
            {
                "counts": {
                    "received": status_counts.get("RECEIVED", 0),
                    "in_progress": status_counts.get("IN_PROGRESS", 0),
                    "ready": status_counts.get("READY", 0),
                },
                "ready_list": WorkOrderListSerializer(ready, many=True).data,
                "pending_payment": WorkOrderListSerializer(pending, many=True).data,
            }
        )

    @action(detail=False, methods=["get"])
    def estadisticas(self, request):
        from decimal import Decimal
        from datetime import date
        from django.db.models import (
            Count, Sum, F, DecimalField, ExpressionWrapper, Subquery, OuterRef, Q
        )
        from django.db.models.functions import Coalesce, TruncMonth

        brand = request.query_params.get("brand", "").strip()
        equipment_type = request.query_params.get("equipment_type", "").strip()
        fault_type_filter = request.query_params.get("fault_type", "").strip()
        date_from = request.query_params.get("date_from", "").strip()
        date_to = request.query_params.get("date_to", "").strip()

        filters = Q()
        if brand:
            filters &= Q(equipment__brand__icontains=brand)
        if equipment_type:
            filters &= Q(equipment__type=equipment_type)
        if fault_type_filter:
            filters &= Q(fault_type=fault_type_filter)
        if date_from:
            filters &= Q(intake_date__gte=date_from)
        if date_to:
            filters &= Q(intake_date__lte=date_to)

        line_total_sq = (
            WorkOrderLine.objects
            .filter(work_order=OuterRef("pk"))
            .values("work_order")
            .annotate(s=Sum(
                ExpressionWrapper(
                    F("unit_price") * F("quantity"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            ))
            .values("s")
        )

        base_qs = (
            WorkOrder.objects
            .filter(filters)
            .select_related("equipment")
            .annotate(
                line_total=Coalesce(
                    Subquery(line_total_sq, output_field=DecimalField(max_digits=12, decimal_places=2)),
                    Decimal("0"),
                )
            )
            .annotate(
                total_ot=ExpressionWrapper(
                    F("line_total") + F("adjustment"),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )
        )

        total_ots_count = WorkOrder.objects.filter(filters).count()
        equipos_atendidos = (
            WorkOrder.objects.filter(filters)
            .values("equipment_id").distinct().count()
        )
        # Sumar líneas directamente para evitar problemas con Sum sobre ExpressionWrapper anidado
        ot_ids = WorkOrder.objects.filter(filters).values_list("id", flat=True)
        facturado_lineas = (
            WorkOrderLine.objects.filter(work_order_id__in=ot_ids)
            .aggregate(
                total=Coalesce(Sum(
                    ExpressionWrapper(
                        F("unit_price") * F("quantity"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ), Decimal("0"))
            )["total"]
        )
        facturado_ajustes = (
            WorkOrder.objects.filter(filters)
            .aggregate(total=Coalesce(Sum("adjustment"), Decimal("0")))["total"]
        )
        total_facturado = facturado_lineas + facturado_ajustes

        por_marca = list(
            base_qs
            .values("equipment__brand")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        fault_labels = dict(WorkOrder.FAULT_TYPE_CHOICES)
        por_tipo_falla = list(
            WorkOrder.objects.filter(filters)
            .exclude(fault_type="")
            .values("fault_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        servicios_top = list(
            WorkOrderLine.objects.filter(work_order_id__in=ot_ids, line_type="SERVICE")
            .values("description")
            .annotate(
                count=Count("id"),
                total=Coalesce(Sum(
                    ExpressionWrapper(
                        F("unit_price") * F("quantity"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ), Decimal("0"))
            )
            .order_by("-count")[:10]
        )

        productos_top = list(
            WorkOrderLine.objects.filter(work_order_id__in=ot_ids, line_type="PRODUCT")
            .values("description")
            .annotate(
                count=Count("id"),
                total=Coalesce(Sum(
                    ExpressionWrapper(
                        F("unit_price") * F("quantity"),
                        output_field=DecimalField(max_digits=12, decimal_places=2),
                    )
                ), Decimal("0"))
            )
            .order_by("-count")[:10]
        )

        today = date.today()
        twelve_ago = date(today.year - 1, today.month, 1)
        por_mes_qs = list(
            WorkOrder.objects.filter(filters, intake_date__gte=twelve_ago)
            .annotate(mes=TruncMonth("intake_date"))
            .values("mes")
            .annotate(ots=Count("id"))
            .order_by("mes")
        )

        return Response({
            "totales": {
                "ots": total_ots_count,
                "equipos_atendidos": equipos_atendidos,
                "facturado": str(total_facturado),
            },
            "por_marca": [
                {"brand": r["equipment__brand"] or "Sin marca", "count": r["count"]}
                for r in por_marca
            ],
            "por_tipo_falla": [
                {"fault_type": r["fault_type"], "label": fault_labels.get(r["fault_type"], r["fault_type"]), "count": r["count"]}
                for r in por_tipo_falla
            ],
            "servicios_top": [
                {"description": r["description"], "count": r["count"], "total": str(r["total"])}
                for r in servicios_top
            ],
            "productos_top": [
                {"description": r["description"], "count": r["count"], "total": str(r["total"])}
                for r in productos_top
            ],
            "por_mes": [
                {"mes": r["mes"].strftime("%Y-%m"), "ots": r["ots"]}
                for r in por_mes_qs
            ],
        })

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
