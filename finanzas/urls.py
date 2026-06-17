from rest_framework.routers import DefaultRouter

from .views import FinancialTransactionViewSet, FundMovementViewSet

router = DefaultRouter()
router.register("transactions", FinancialTransactionViewSet, basename="financialtransaction")
router.register("fund-movements", FundMovementViewSet, basename="fundmovement")

urlpatterns = router.urls
