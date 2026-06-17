from rest_framework import viewsets

from .models import InventoryMovement, Product, ProductCategory, Supplier
from .serializers import (
    InventoryMovementSerializer,
    ProductCategorySerializer,
    ProductSerializer,
    SupplierSerializer,
)


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
    queryset = Product.objects.select_related("category", "supplier").all()
    serializer_class = ProductSerializer
    filterset_fields = ["category", "supplier"]
    search_fields = ["code", "name"]
    ordering_fields = ["code", "name", "sale_price", "purchase_price"]
    ordering = ["code"]


class InventoryMovementViewSet(viewsets.ModelViewSet):
    queryset = InventoryMovement.objects.select_related("product").all()
    serializer_class = InventoryMovementSerializer
    filterset_fields = ["product", "movement_type"]
    search_fields = ["reference"]
    ordering_fields = ["date", "quantity"]
    ordering = ["-date"]
