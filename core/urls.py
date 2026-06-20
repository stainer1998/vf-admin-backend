from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AllocationFundViewSet, DiskInterpretationViewSet, EquipmentLevelViewSet, EmpresaConfigView

router = DefaultRouter()
router.register("allocation-funds", AllocationFundViewSet, basename="allocationfund")
router.register("disk-interpretations", DiskInterpretationViewSet, basename="diskinterpretation")
router.register("equipment-levels", EquipmentLevelViewSet, basename="equipmentlevel")

urlpatterns = router.urls + [
    path("empresa/", EmpresaConfigView.as_view(), name="empresa-config"),
]
