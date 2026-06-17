from rest_framework.routers import DefaultRouter

from .views import EquipmentViewSet

router = DefaultRouter()
router.register("equipment", EquipmentViewSet, basename="equipment")

urlpatterns = router.urls
