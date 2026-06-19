from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Brand, InventoryMovement, Product, ProductCategory, Supplier
from .serializers import (
    BrandSerializer,
    InventoryMovementSerializer,
    ProductCategorySerializer,
    ProductSerializer,
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
    filterset_fields = ["is_stockable"]


class SupplierViewSet(viewsets.ModelViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    search_fields = ["name"]
    ordering_fields = ["name"]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.select_related("category", "supplier", "brand").all()
    serializer_class = ProductSerializer
    filterset_fields = ["category", "supplier"]
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
        )
        return Response(ProductSerializer(qs, many=True).data)


class InventoryMovementViewSet(viewsets.ModelViewSet):
    queryset = InventoryMovement.objects.select_related("product").all()
    serializer_class = InventoryMovementSerializer
    filterset_fields = ["product", "movement_type"]
    search_fields = ["reference"]
    ordering_fields = ["date", "quantity"]
    ordering = ["-date"]
