from decimal import Decimal

from django.db import transaction
from rest_framework import serializers as drf_serializers
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response

from .models import AllocationFund, DiskInterpretation, EquipmentLevel, EmpresaConfig
from .serializers import (
    AllocationFundSerializer,
    DiskInterpretationSerializer,
    EquipmentLevelSerializer,
    EmpresaConfigSerializer,
)


class AllocationFundViewSet(viewsets.ModelViewSet):
    queryset = AllocationFund.objects.all()
    serializer_class = AllocationFundSerializer
    ordering_fields = ["order", "name", "percentage"]
    pagination_class = None  # always return full list

    @action(detail=False, methods=["post"], url_path="ajustar_porcentajes")
    def ajustar_porcentajes(self, request):
        """Atomically update percentage/is_active for a set of funds.

        Body: {"funds": [{"id": 1, "percentage": "35.00", "is_active": true}, ...]}
        Validates that active funds (after applying the changes) sum to exactly
        100% before committing anything.
        """

        class FundAdjustmentSerializer(drf_serializers.Serializer):
            id = drf_serializers.IntegerField()
            percentage = drf_serializers.DecimalField(max_digits=5, decimal_places=2)
            is_active = drf_serializers.BooleanField()

        class AjusteSerializer(drf_serializers.Serializer):
            funds = FundAdjustmentSerializer(many=True)

        ser = AjusteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        adjustments = {f["id"]: f for f in ser.validated_data["funds"]}

        funds = list(AllocationFund.objects.filter(pk__in=adjustments.keys()))
        if len(funds) != len(adjustments):
            return Response({"detail": "Uno o más fondos no existen."}, status=status.HTTP_400_BAD_REQUEST)

        total_active = Decimal("0")
        for fund in funds:
            adj = adjustments[fund.pk]
            if adj["is_active"]:
                total_active += adj["percentage"]

        if total_active != Decimal("100"):
            return Response(
                {"detail": f"Los fondos activos deben sumar 100%. Total enviado: {total_active}%."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            for fund in funds:
                adj = adjustments[fund.pk]
                fund.percentage = adj["percentage"]
                fund.is_active = adj["is_active"]
                fund.save(update_fields=["percentage", "is_active"])

        return Response(AllocationFundSerializer(funds, many=True).data)


class DiskInterpretationViewSet(viewsets.ModelViewSet):
    queryset = DiskInterpretation.objects.all()
    serializer_class = DiskInterpretationSerializer
    search_fields = ["pattern", "manufacturer"]
    filterset_fields = ["disk_type"]


class EquipmentLevelViewSet(viewsets.ModelViewSet):
    queryset = EquipmentLevel.objects.all()
    serializer_class = EquipmentLevelSerializer
    ordering_fields = ["order", "name"]


class EmpresaConfigView(RetrieveUpdateAPIView):
    serializer_class = EmpresaConfigSerializer

    def get_object(self):
        return EmpresaConfig.get_instance()
