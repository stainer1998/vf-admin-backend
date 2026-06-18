from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Case, DecimalField, Q, Sum, When
from django.db.models.functions import TruncMonth
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
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

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """Financial summary for dashboards: monthly stats + fund distribution + current month KPIs."""
        today = date.today()
        twelve_months_ago = date(today.year - 1, today.month, 1)

        # Monthly income/expense for last 12 months
        monthly_qs = (
            FinancialTransaction.objects.filter(date__gte=twelve_months_ago)
            .annotate(month=TruncMonth("date"))
            .values("month", "transaction_type")
            .annotate(total=Sum("amount"))
            .order_by("month")
        )

        # Build a dict keyed by "YYYY-MM" with income/expense slots
        monthly_map: dict[str, dict] = {}
        for row in monthly_qs:
            key = row["month"].strftime("%Y-%m")
            if key not in monthly_map:
                monthly_map[key] = {"month": key, "income": 0, "expense": 0, "adjustment": 0}
            t = row["transaction_type"]
            if t == FinancialTransaction.INCOME:
                monthly_map[key]["income"] = float(row["total"])
            elif t == FinancialTransaction.EXPENSE:
                monthly_map[key]["expense"] = float(row["total"])
            else:
                monthly_map[key]["adjustment"] = float(row["total"])

        # Fill months with no data
        all_months = []
        cursor = twelve_months_ago
        while cursor <= today:
            key = cursor.strftime("%Y-%m")
            entry = monthly_map.get(key, {"month": key, "income": 0, "expense": 0, "adjustment": 0})
            entry["net"] = entry["income"] - entry["expense"]
            all_months.append(entry)
            # advance to next month
            if cursor.month == 12:
                cursor = date(cursor.year + 1, 1, 1)
            else:
                cursor = date(cursor.year, cursor.month + 1, 1)

        # Fund distribution — total credited per fund across all time
        fund_dist = []
        for fund in AllocationFund.objects.filter(is_active=True):
            total = (
                FundMovement.objects.filter(fund=fund, movement_type=FundMovement.CREDIT)
                .aggregate(t=Sum("amount"))["t"]
                or Decimal("0")
            )
            fund_dist.append({
                "fund_id": fund.pk,
                "fund_name": fund.name,
                "color": fund.color,
                "percentage": float(fund.percentage),
                "total_credited": float(total),
            })

        # Current month KPIs
        month_start = date(today.year, today.month, 1)
        month_qs = FinancialTransaction.objects.filter(date__gte=month_start)
        income_month = month_qs.filter(
            transaction_type=FinancialTransaction.INCOME
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")
        expense_month = month_qs.filter(
            transaction_type=FinancialTransaction.EXPENSE
        ).aggregate(t=Sum("amount"))["t"] or Decimal("0")

        from trabajos.models import WorkOrder
        pending_ots = WorkOrder.objects.filter(payment_status=WorkOrder.PENDING)
        pending_count = pending_ots.count()
        pending_amount = sum(ot.amount_charged for ot in pending_ots)

        return Response({
            "monthly": all_months,
            "fund_distribution": fund_dist,
            "current_month": {
                "income": float(income_month),
                "expense": float(expense_month),
                "net": float(income_month - expense_month),
                "pending_ots_count": pending_count,
                "pending_ots_amount": float(pending_amount),
            },
        })

    @action(detail=False, methods=["post"])
    def cash_adjustment(self, request):
        """Register a manual cash injection or withdrawal."""

        class AdjustmentSerializer(drf_serializers.Serializer):
            direction = drf_serializers.ChoiceField(choices=["INJECTION", "WITHDRAWAL"])
            amount = drf_serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
            description = drf_serializers.CharField(max_length=300)
            date = drf_serializers.DateField()
            fund = drf_serializers.IntegerField(allow_null=True, required=False, default=None)

        ser = AdjustmentSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data

        tx = FinancialTransaction.objects.create(
            transaction_type=FinancialTransaction.ADJUSTMENT,
            date=d["date"],
            amount=d["amount"],
            description=d["description"],
        )

        movement_type = FundMovement.CREDIT if d["direction"] == "INJECTION" else FundMovement.DEBIT

        if d["fund"] is not None:
            try:
                fund = AllocationFund.objects.get(pk=d["fund"], is_active=True)
            except AllocationFund.DoesNotExist:
                tx.delete()
                return Response({"fund": "Fondo no encontrado."}, status=status.HTTP_400_BAD_REQUEST)
            FundMovement.objects.create(
                fund=fund,
                movement_type=movement_type,
                amount=d["amount"],
                date=d["date"],
                reference=f"Ajuste: {d['description'][:100]}",
            )
        else:
            funds = AllocationFund.objects.filter(is_active=True)
            for fund in funds:
                fund_amount = (d["amount"] * fund.percentage / Decimal("100")).quantize(Decimal("0.01"))
                FundMovement.objects.create(
                    fund=fund,
                    movement_type=movement_type,
                    amount=fund_amount,
                    date=d["date"],
                    reference=f"Ajuste: {d['description'][:100]}",
                )

        return Response(FinancialTransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class FundMovementViewSet(viewsets.ModelViewSet):
    queryset = FundMovement.objects.select_related("fund").all()
    serializer_class = FundMovementSerializer
    filterset_fields = ["fund", "movement_type"]
    ordering_fields = ["date", "amount"]
    ordering = ["-date"]

    @action(detail=False, methods=["get"])
    def balances(self, request):
        """Return current balance for each active fund."""
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
                "color": fund.color,
                "percentage": float(fund.percentage),
                "balance": float(credits - debits),
            })
        return Response(result)
