import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from catalogo.models import Service

from .models import HistorialCalculo, ParametrosCalculadora
from .serializers import (
    ActualizarServicioSerializer,
    CalculoInputSerializer,
    GuardarServicioSerializer,
    HistorialSerializer,
    ParametrosSerializer,
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

        if Service.objects.filter(code=data["codigo"]).exists():
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
