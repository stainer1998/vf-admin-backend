from rest_framework import serializers

from .models import Allocation, AllocationDetail, FinancialTransaction, FundMovement


class AllocationDetailSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source="fund.name", read_only=True)

    class Meta:
        model = AllocationDetail
        fields = ["id", "fund", "fund_name", "percentage_applied", "amount"]


class AllocationSerializer(serializers.ModelSerializer):
    details = AllocationDetailSerializer(many=True, read_only=True)

    class Meta:
        model = Allocation
        fields = ["id", "transaction", "generated_at", "details"]
        read_only_fields = ["generated_at"]


class FinancialTransactionSerializer(serializers.ModelSerializer):
    allocation = AllocationSerializer(read_only=True)

    class Meta:
        model = FinancialTransaction
        fields = [
            "id",
            "transaction_type",
            "date",
            "amount",
            "description",
            "work_order",
            "inventory_movement",
            "created_at",
            "allocation",
        ]
        read_only_fields = ["created_at"]


class FinancialTransactionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits nested allocation."""

    class Meta:
        model = FinancialTransaction
        fields = [
            "id",
            "transaction_type",
            "date",
            "amount",
            "description",
            "work_order",
            "inventory_movement",
            "created_at",
        ]
        read_only_fields = ["created_at"]


class FundMovementSerializer(serializers.ModelSerializer):
    fund_name = serializers.CharField(source="fund.name", read_only=True)

    class Meta:
        model = FundMovement
        fields = ["id", "fund", "fund_name", "movement_type", "amount", "date", "reference"]
