from rest_framework.routers import DefaultRouter

from .views import AllocationFundViewSet, DiskInterpretationViewSet, EquipmentLevelViewSet

router = DefaultRouter()
router.register("allocation-funds", AllocationFundViewSet, basename="allocationfund")
router.register("disk-interpretations", DiskInterpretationViewSet, basename="diskinterpretation")
router.register("equipment-levels", EquipmentLevelViewSet, basename="equipmentlevel")

urlpatterns = router.urls
