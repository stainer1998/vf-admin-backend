from rest_framework.routers import DefaultRouter

from .views import DiagnosisViewSet, StorageDeviceViewSet

router = DefaultRouter()
router.register("diagnoses", DiagnosisViewSet, basename="diagnosis")
router.register("storage-devices", StorageDeviceViewSet, basename="storagedevice")

urlpatterns = router.urls
