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

    @action(detail=True, methods=["get"])
    def bitacora(self, request, pk=None):
        from decimal import Decimal
        from django.db.models import (
            Count, Sum, F, DecimalField, ExpressionWrapper, Subquery, OuterRef
        )
        from django.db.models.functions import Coalesce
        from trabajos.models import WorkOrder, WorkOrderLine

        equipment = self.get_object()

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

        ots_qs = (
            WorkOrder.objects
            .filter(equipment=equipment)
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
            .prefetch_related("lines")
            .order_by("-intake_date")
        )

        ots = list(ots_qs)

        total_facturado = sum((ot.total_ot for ot in ots), Decimal("0"))
        primera_ot = ots[-1].intake_date.isoformat() if ots else None
        ultima_ot = ots[0].intake_date.isoformat() if ots else None

        _line_agg = lambda line_type: (  # noqa: E731
            WorkOrderLine.objects
            .filter(work_order__equipment=equipment, line_type=line_type)
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

        fault_labels = dict(WorkOrder.FAULT_TYPE_CHOICES)
        fallas_qs = (
            WorkOrder.objects
            .filter(equipment=equipment)
            .exclude(fault_type="")
            .values("fault_type")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        def _serialize_ot(ot):
            return {
                "id": ot.id,
                "number": ot.number,
                "intake_date": ot.intake_date.isoformat(),
                "delivery_date": ot.delivery_date.isoformat() if ot.delivery_date else None,
                "work_status": ot.work_status,
                "payment_status": ot.payment_status,
                "amount_charged": str(ot.total_ot),
                "fault_type": ot.fault_type,
                "work_description": ot.work_description,
                "lines": [
                    {
                        "line_type": l.line_type,
                        "description": l.description,
                        "quantity": l.quantity,
                        "unit_price": str(l.unit_price),
                    }
                    for l in ot.lines.all()
                ],
            }

        return Response({
            "equipment": {
                "id": equipment.id,
                "type": equipment.type,
                "brand": equipment.brand,
                "model": equipment.model,
                "serial_number": equipment.serial_number,
                "year": equipment.year,
                "client_name": str(equipment.client),
            },
            "stats": {
                "total_ots": len(ots),
                "total_facturado": str(total_facturado),
                "primera_ot": primera_ot,
                "ultima_ot": ultima_ot,
            },
            "ots": [_serialize_ot(ot) for ot in ots],
            "servicios_frecuentes": [
                {"description": r["description"], "count": r["count"], "total": str(r["total"])}
                for r in _line_agg("SERVICE")
            ],
            "productos_frecuentes": [
                {"description": r["description"], "count": r["count"], "total": str(r["total"])}
                for r in _line_agg("PRODUCT")
            ],
            "fallas_frecuentes": [
                {"fault_type": r["fault_type"], "label": fault_labels.get(r["fault_type"], r["fault_type"]), "count": r["count"]}
                for r in fallas_qs
            ],
        })

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
