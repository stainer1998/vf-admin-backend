from rest_framework.routers import DefaultRouter

from .views import (
    InventoryMovementViewSet,
    ProductCategoryViewSet,
    ProductViewSet,
    SupplierViewSet,
)

router = DefaultRouter()
router.register("product-categories", ProductCategoryViewSet, basename="productcategory")
router.register("suppliers", SupplierViewSet, basename="supplier")
router.register("products", ProductViewSet, basename="product")
router.register("inventory-movements", InventoryMovementViewSet, basename="inventorymovement")

urlpatterns = router.urls
