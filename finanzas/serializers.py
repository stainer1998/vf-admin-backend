from rest_framework import serializers

from .models import (
    Allocation, AlertaFinanciera, AllocationDetail, ExpenseCategory,
    FinancialTransaction, FundMovement, GastoPendiente, GastoRecurrente,
)


class ExpenseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ExpenseCategory
        fields = ["id", "name", "category_type", "color", "is_active", "order"]


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
    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = FinancialTransaction
        fields = [
            "id",
            "transaction_type",
            "date",
            "amount",
            "description",
            "category",
            "category_name",
            "work_order",
            "inventory_movement",
            "created_at",
            "allocation",
        ]
        read_only_fields = ["created_at"]


class FinancialTransactionListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views — omits nested allocation."""

    category_name = serializers.CharField(source="category.name", read_only=True, default=None)

    class Meta:
        model = FinancialTransaction
        fields = [
            "id",
            "transaction_type",
            "date",
            "amount",
            "description",
            "category",
            "category_name",
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


class GastoRecurrenteSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.name", read_only=True, default=None)

    class Meta:
        model = GastoRecurrente
        fields = ["id", "nombre", "descripcion", "monto", "categoria", "categoria_nombre", "dia_del_mes", "activo"]


class GastoPendienteSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.name", read_only=True, default=None)
    work_order_numero = serializers.CharField(source="work_order.number", read_only=True, default=None)

    class Meta:
        model = GastoPendiente
        fields = [
            "id", "descripcion", "monto", "categoria", "categoria_nombre",
            "work_order", "work_order_numero", "estado", "transaction",
            "fecha_estimada", "confirmado_en", "notas", "created_at",
        ]
        read_only_fields = ["estado", "transaction", "confirmado_en", "created_at"]


class AlertaFinancieraSerializer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source="get_tipo_display", read_only=True)
    severidad_display = serializers.CharField(source="get_severidad_display", read_only=True)

    class Meta:
        model = AlertaFinanciera
        fields = [
            "id", "tipo", "tipo_display", "severidad", "severidad_display",
            "mensaje", "fecha", "activa", "resuelta_en",
        ]
        read_only_fields = ["tipo", "severidad", "mensaje", "fecha", "resuelta_en"]
