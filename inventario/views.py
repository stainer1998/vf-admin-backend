from datetime import date

from django.db import transaction
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    Brand, InventoryMovement, Product, ProductCategory,
    ProductSupplier, PurchaseOrder, PurchaseOrderLine, Supplier,
)
from .serializers import (
    BrandSerializer,
    InventoryMovementSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    PurchaseOrderListSerializer,
    PurchaseOrderSerializer,
    SupplierSerializer,
)


class BrandViewSet(viewsets.ModelViewSet):
    queryset = Brand.objects.all().order_by("name")
    serializer_class = BrandSerializer
    search_fields = ["name"]


class ProductCategoryViewSet(viewsets.ModelViewSet):
    queryset = ProductCategory.objects.all()
    serializer_class = ProductCategorySerializer
    search_fields = ["name"]
    filterset_fields = ["is_stockable", "is_equipment_component"]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]


def _product_suppliers_prefetch():
    return Prefetch(
        "product_suppliers",
        queryset=ProductSupplier.objects.select_related("supplier").order_by(
            "-is_preferred", "supplier__name"
        ),
    )


class ProductViewSet(viewsets.ModelViewSet):
    queryset = (
        Product.objects.select_related("category", "brand")
        .prefetch_related(_product_suppliers_prefetch())
        .all()
    )
    serializer_class = ProductSerializer
    filterset_fields = ["category", "suppliers"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "sale_price", "purchase_price"]
    ordering = ["code"]

    @action(detail=False, methods=["get"], url_path="out-of-stock")
    def out_of_stock(self, request):
        from django.db.models import Case, F, IntegerField, Q, Sum, Value, When

        qs = (
            Product.objects.filter(category__is_stockable=True)
            .annotate(
                computed_stock=Sum(
                    Case(
                        When(movements__movement_type="ENTRY", then=F("movements__quantity")),
                        When(movements__movement_type="EXIT", then=-F("movements__quantity")),
                        When(movements__movement_type="ADJUSTMENT", then=F("movements__quantity")),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            )
            .filter(Q(computed_stock__lte=0) | Q(computed_stock__isnull=True))
            .select_related("category")
            .prefetch_related(_product_suppliers_prefetch())
        )
        return Response(ProductSerializer(qs, many=True).data)


class InventoryMovementViewSet(viewsets.ModelViewSet):
    queryset = InventoryMovement.objects.select_related("product").all()
    serializer_class = InventoryMovementSerializer
    filterset_fields = ["product", "movement_type"]
    search_fields = ["reference"]
    ordering_fields = ["date", "quantity"]
    ordering = ["-date"]


class PurchaseOrderViewSet(viewsets.ModelViewSet):
    queryset = (
        PurchaseOrder.objects
        .select_related("supplier")
        .prefetch_related("lines__product")
        .all()
    )
    filterset_fields = ["status", "supplier"]
    search_fields = ["number", "supplier__name"]
    ordering_fields = ["date", "created_at"]
    ordering = ["-created_at"]

    def get_serializer_class(self):
        if self.action == "list":
            return PurchaseOrderListSerializer
        return PurchaseOrderSerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != PurchaseOrder.DRAFT:
            return Response(
                {"detail": "Solo se pueden editar órdenes en borrador."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.status != PurchaseOrder.DRAFT:
            return Response(
                {"detail": "Solo se pueden eliminar órdenes en borrador."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        po = self.get_object()
        if po.status != PurchaseOrder.DRAFT:
            return Response(
                {"detail": "Solo se pueden confirmar órdenes en borrador."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = PurchaseOrder.CONFIRMED
        po.save()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        po = self.get_object()
        if po.status in (PurchaseOrder.RECEIVED, PurchaseOrder.CANCELLED):
            return Response(
                {"detail": "No se puede cancelar una orden ya recibida o cancelada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        po.status = PurchaseOrder.CANCELLED
        po.save()
        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"], url_path="receive-line")
    def receive_line(self, request, pk=None):
        po = self.get_object()
        if po.status not in (PurchaseOrder.CONFIRMED, PurchaseOrder.PARTIALLY_RECEIVED):
            return Response(
                {"detail": "La orden debe estar Confirmada para recibir mercadería."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        line_id = request.data.get("line_id")
        try:
            quantity = int(request.data.get("quantity", 0))
        except (TypeError, ValueError):
            return Response({"detail": "Cantidad inválida."}, status=status.HTTP_400_BAD_REQUEST)

        if not line_id:
            return Response({"detail": "line_id es requerido."}, status=status.HTTP_400_BAD_REQUEST)

        line = get_object_or_404(PurchaseOrderLine, pk=line_id, purchase_order=po)

        if quantity <= 0:
            return Response({"detail": "La cantidad debe ser mayor a cero."}, status=status.HTTP_400_BAD_REQUEST)
        if quantity > line.pending_quantity:
            return Response(
                {"detail": f"Cantidad excede el pendiente ({line.pending_quantity})."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        InventoryMovement.objects.create(
            product=line.product,
            movement_type=InventoryMovement.ENTRY,
            quantity=quantity,
            unit_cost=line.unit_cost,
            date=date.today(),
            reference=po.number,
            notes=f"Recepción OC {po.number}",
        )

        line.quantity_received += quantity
        line.save()

        lines = list(po.lines.all())
        if all(l.is_fully_received for l in lines):
            po.status = PurchaseOrder.RECEIVED
        else:
            po.status = PurchaseOrder.PARTIALLY_RECEIVED
        po.save()

        return Response(PurchaseOrderSerializer(po).data)

    @action(detail=True, methods=["post"], url_path="receive-all")
    def receive_all(self, request, pk=None):
        po = self.get_object()
        if po.status not in (PurchaseOrder.CONFIRMED, PurchaseOrder.PARTIALLY_RECEIVED):
            return Response(
                {"detail": "La orden debe estar Confirmada para recibir mercadería."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        lines = list(po.lines.all())
        if not lines:
            return Response({"detail": "La orden no tiene líneas."}, status=status.HTTP_400_BAD_REQUEST)

        pending_lines = [line for line in lines if line.pending_quantity > 0]
        if not pending_lines:
            # Every line is already fully received (e.g. quantities were
            # corrected outside this endpoint) but the order status is stale.
            # Reconcile it instead of erroring — there's nothing left to move.
            po.status = PurchaseOrder.RECEIVED
            po.save()
            return Response(PurchaseOrderSerializer(po).data)

        with transaction.atomic():
            for line in pending_lines:
                InventoryMovement.objects.create(
                    product=line.product,
                    movement_type=InventoryMovement.ENTRY,
                    quantity=line.pending_quantity,
                    unit_cost=line.unit_cost,
                    date=date.today(),
                    reference=po.number,
                    notes=f"Recepción OC {po.number}",
                )
                line.quantity_received = line.quantity_ordered
                line.save()

            po.status = PurchaseOrder.RECEIVED
            po.save()

        return Response(PurchaseOrderSerializer(po).data)
