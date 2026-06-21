from rest_framework.routers import DefaultRouter

from .views import (
    AlertaFinancieraViewSet, ExpenseCategoryViewSet, FinancialTransactionViewSet,
    FundMovementViewSet, GastoPendienteViewSet, GastoRecurrenteViewSet,
)

router = DefaultRouter()
router.register("transactions", FinancialTransactionViewSet, basename="financialtransaction")
router.register("fund-movements", FundMovementViewSet, basename="fundmovement")
router.register("expense-categories", ExpenseCategoryViewSet, basename="expensecategory")
router.register("gastos-recurrentes", GastoRecurrenteViewSet, basename="gastorecurrente")
router.register("gastos-pendientes", GastoPendienteViewSet, basename="gastopendiente")
router.register("alertas", AlertaFinancieraViewSet, basename="alertafinanciera")

urlpatterns = router.urls
