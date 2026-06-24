from rest_framework.routers import DefaultRouter

from .views import (
    BrandViewSet,
    InventoryMovementViewSet,
    ProductCategoryViewSet,
    ProductViewSet,
    PurchaseOrderViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("brands", BrandViewSet, basename="brand")
router.register("product-categories", ProductCategoryViewSet, basename="productcategory")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("products", ProductViewSet, basename="product")
router.register("inventory-movements", InventoryMovementViewSet, basename="inventorymovement")
router.register("purchase-orders", PurchaseOrderViewSet, basename="purchaseorder")

urlpatterns = router.urls
