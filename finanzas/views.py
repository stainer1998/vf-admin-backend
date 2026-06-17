from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import AllocationFund
from .models import Allocation, AllocationDetail, FinancialTransaction, FundMovement
from .serializers import (
    FinancialTransactionListSerializer,
    FinancialTransactionSerializer,
    FundMovementSerializer,
)


class FinancialTransactionViewSet(viewsets.ModelViewSet):
    queryset = FinancialTransaction.objects.select_related(
        "work_order", "inventory_movement"
    ).prefetch_related("allocation__details__fund").all()
    filterset_fields = ["transaction_type", "work_order"]
    search_fields = ["description"]
    ordering_fields = ["date", "amount"]
    ordering = ["-date"]

    def get_serializer_class(self):
        if self.action == "list":
            return FinancialTransactionListSerializer
        return FinancialTransactionSerializer


class FundMovementViewSet(viewsets.ModelViewSet):
    queryset = FundMovement.objects.select_related("fund").all()
    serializer_class = FundMovementSerializer
    filterset_fields = ["fund", "movement_type"]
    ordering_fields = ["date", "amount"]
    ordering = ["-date"]

    @action(detail=False, methods=["get"])
    def balances(self, request):
        """Return current balance for each active fund."""
        from django.db.models import Case, DecimalField, Sum, When, F
        from decimal import Decimal

        funds = AllocationFund.objects.filter(is_active=True)
        result = []
        for fund in funds:
            credits = FundMovement.objects.filter(
                fund=fund, movement_type=FundMovement.CREDIT
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            debits = FundMovement.objects.filter(
                fund=fund, movement_type=FundMovement.DEBIT
            ).aggregate(total=Sum("amount"))["total"] or Decimal("0")
            result.append({
                "fund_id": fund.pk,
                "fund_name": fund.name,
                "balance": credits - debits,
            })
        return Response(result)
