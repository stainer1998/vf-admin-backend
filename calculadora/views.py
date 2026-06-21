import logging
from datetime import date

from django.db.models import F, Q, Sum
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Service
from finanzas.models import FinancialTransaction
from trabajos.models import WorkOrderLine

from .models import HistorialCalculo, ParametrosCalculadora
from .serializers import (
    ActualizarServicioSerializer,
    CalculoInputSerializer,
    GuardarServicioSerializer,
    HistorialSerializer,
    ParametrosSerializer,
    ParametrosWriteSerializer,
    ejecutar_calculo,
)

logger = logging.getLogger(__name__)


def _get_parametros_activos():
    return ParametrosCalculadora.objects.filter(activo=True).first()


class ParametrosView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = _get_parametros_activos()
        if not params:
            return Response(
                {"detail": "No hay parámetros configurados. Configúralos desde el admin."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ParametrosSerializer(params).data)


class ActualizarParametrosView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.rol != "ADMIN":
            return Response(
                {"detail": "Solo los administradores pueden modificar los parámetros."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = ParametrosWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = ParametrosCalculadora.objects.create(
            **serializer.validated_data,
            usuario_actualizacion=request.user,
            activo=True,
        )
        logger.info("Parámetros calculadora actualizados por usuario=%s", request.user.username)
        return Response(ParametrosSerializer(params).data, status=status.HTTP_201_CREATED)


class CalcularView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CalculoInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        params = _get_parametros_activos()
        if not params:
            return Response(
                {"detail": "No hay parámetros configurados."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = ejecutar_calculo(params, serializer.validated_data)

        HistorialCalculo.objects.create(
            usuario=request.user,
            parametros_input=serializer.validated_data,
            resultado_calculo=resultado,
        )
        logger.info("Cálculo realizado por usuario=%s", request.user.username)

        return Response(resultado)


class GuardarComoServicioView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = GuardarServicioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["codigo"] and Service.objects.filter(code=data["codigo"]).exists():
            return Response(
                {"codigo": ["Ya existe un servicio con este código."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        params = _get_parametros_activos()
        if not params:
            return Response(
                {"detail": "No hay parámetros configurados."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = ejecutar_calculo(params, data["datos_calculo"])

        service = Service.objects.create(
            code=data["codigo"],
            name=data["nombre"],
            description=data["descripcion"],
            sale_price=data["precio_final"],
            direct_cost=resultado["desglose"]["costo_total"],
            metadata_calculo={
                "datos_calculo": {
                    k: str(v) for k, v in data["datos_calculo"].items()
                },
                "resultado": resultado,
            },
        )

        HistorialCalculo.objects.create(
            usuario=request.user,
            parametros_input=data["datos_calculo"],
            resultado_calculo=resultado,
            servicio_guardado=service,
        )
        logger.info(
            "Servicio creado desde calculadora: %s por usuario=%s",
            service.code,
            request.user.username,
        )

        return Response(
            {
                "servicio_id": service.pk,
                "codigo": service.code,
                "nombre": service.name,
                "sale_price": str(service.sale_price),
                "resultado": resultado,
            },
            status=status.HTTP_201_CREATED,
        )


class ActualizarServicioView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        service = get_object_or_404(Service, pk=pk)
        serializer = ActualizarServicioSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        params = _get_parametros_activos()
        if not params:
            return Response(
                {"detail": "No hay parámetros configurados."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        resultado = ejecutar_calculo(params, data["datos_calculo"])

        service.sale_price = data["precio_final"]
        service.direct_cost = resultado["desglose"]["costo_total"]
        service.metadata_calculo = {
            "datos_calculo": {k: str(v) for k, v in data["datos_calculo"].items()},
            "resultado": resultado,
        }
        service.save()

        HistorialCalculo.objects.create(
            usuario=request.user,
            parametros_input=data["datos_calculo"],
            resultado_calculo=resultado,
            servicio_guardado=service,
        )
        logger.info(
            "Servicio actualizado desde calculadora: %s por usuario=%s",
            service.code,
            request.user.username,
        )

        return Response(
            {
                "servicio_id": service.pk,
                "codigo": service.code,
                "nombre": service.name,
                "sale_price": str(service.sale_price),
                "resultado": resultado,
            }
        )


class AnalisisFinancieroView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        params = _get_parametros_activos()
        if not params:
            return Response(
                {"detail": "No hay parámetros configurados.", "sin_parametros": True},
                status=status.HTTP_200_OK,
            )

        mes_param = request.query_params.get("mes")
        if mes_param:
            try:
                year, month = (int(p) for p in mes_param.split("-"))
            except (ValueError, AttributeError):
                return Response({"detail": "Formato de mes inválido. Use YYYY-MM."}, status=status.HTTP_400_BAD_REQUEST)
        else:
            hoy = date.today()
            year, month = hoy.year, hoy.month

        # Ingresos reales del mes (desde ledger financiero)
        ingreso_real = (
            FinancialTransaction.objects.filter(
                transaction_type="INCOME", date__year=year, date__month=month
            ).aggregate(total=Sum("amount"))["total"]
            or 0
        )

        # OTs PAID con fecha en el mes (delivery_date o intake_date como fallback)
        ots_mes = WorkOrderLine.objects.filter(
            Q(work_order__payment_status="PAID")
            & (
                Q(work_order__delivery_date__year=year, work_order__delivery_date__month=month)
                | Q(work_order__delivery_date__isnull=True, work_order__intake_date__year=year, work_order__intake_date__month=month)
            )
        )

        costos = ots_mes.aggregate(
            costo_total=Sum(F("unit_cost") * F("quantity")),
            costo_labor=Sum(F("unit_cost") * F("quantity"), filter=Q(line_type="SERVICE")),
            costo_materiales=Sum(F("unit_cost") * F("quantity"), filter=Q(line_type="PRODUCT")),
            ingreso_labor=Sum(F("unit_price") * F("quantity"), filter=Q(line_type="SERVICE")),
        )

        costo_directo_total = float(costos["costo_total"] or 0)
        costo_labor = float(costos["costo_labor"] or 0)
        costo_materiales = float(costos["costo_materiales"] or 0)
        ingreso_labor = float(costos["ingreso_labor"] or 0)

        ingreso_real_f = float(ingreso_real)
        objetivo_mensual = float(params.sueldo_objetivo_mensual + params.costos_fijos_mensuales)
        margen_bruto = ingreso_real_f - costo_directo_total
        costo_por_hora = float(params.costo_por_hora)

        cumplimiento_pct = round((ingreso_real_f / objetivo_mensual * 100), 1) if objetivo_mensual > 0 else 0
        margen_bruto_pct = round((margen_bruto / ingreso_real_f * 100), 1) if ingreso_real_f > 0 else 0
        horas_equivalentes = round(ingreso_labor / costo_por_hora, 1) if costo_por_hora > 0 else 0

        return Response({
            "mes": f"{year}-{month:02d}",
            "sin_parametros": False,
            "params": {
                "sueldo_objetivo_mensual": str(params.sueldo_objetivo_mensual),
                "costos_fijos_mensuales": str(params.costos_fijos_mensuales),
                "horas_productivas_mensuales": str(params.horas_productivas_mensuales),
                "costo_por_hora": str(round(costo_por_hora, 0)),
            },
            "objetivo_mensual": objetivo_mensual,
            "ingreso_real": ingreso_real_f,
            "cumplimiento_pct": cumplimiento_pct,
            "costo_directo_total": costo_directo_total,
            "margen_bruto": margen_bruto,
            "margen_bruto_pct": margen_bruto_pct,
            "costo_labor": costo_labor,
            "costo_materiales": costo_materiales,
            "ingreso_labor": ingreso_labor,
            "horas_equivalentes_facturadas": horas_equivalentes,
            "horas_objetivo": float(params.horas_productivas_mensuales),
        })


class HistorialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = HistorialCalculo.objects.select_related(
            "usuario", "servicio_guardado"
        ).all()
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = HistorialSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)
