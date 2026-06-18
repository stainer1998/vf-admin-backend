from decimal import ROUND_HALF_UP, Decimal

from rest_framework import serializers

from .models import HistorialCalculo, ParametrosCalculadora

REDONDEO_CHOICES = [0, 100, 500, 1000]


def _redondear(valor: Decimal, redondear_a: int) -> Decimal:
    if redondear_a == 0:
        return valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    factor = Decimal(redondear_a)
    return (valor / factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * factor


def ejecutar_calculo(params: ParametrosCalculadora, data: dict) -> dict:
    tiempo_horas = Decimal(str(data["tiempo_horas"]))
    transporte = Decimal(str(data["transporte"]))
    desgaste = Decimal(str(data["desgaste_herramientas"]))
    pct_garantia = Decimal(str(data["porcentaje_garantia"]))
    margen = Decimal(str(data["margen_ganancia"]))
    redondear_a = int(data.get("redondear_a", 0))

    cph = params.costo_por_hora
    costo_tiempo = (tiempo_horas * cph).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    provision_garantia = (costo_tiempo * pct_garantia / 100).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    costos_directos_total = transporte + desgaste + provision_garantia
    costo_total = costo_tiempo + costos_directos_total
    precio_calculado = (costo_total * (1 + margen / 100)).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    precio_redondeado = _redondear(precio_calculado, redondear_a)
    precio_con_iva = (precio_redondeado * Decimal("1.19")).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    )
    margen_monto = (precio_calculado - costo_total).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )

    recomendaciones = []
    if margen < 50:
        recomendaciones.append("Margen bajo — considera aumentar el porcentaje de ganancia.")
    if margen > 200:
        recomendaciones.append("Margen muy alto — podría desincentivar al cliente.")
    if tiempo_horas > 8:
        recomendaciones.append(
            "Trabajo extenso — considera dividir en múltiples servicios."
        )
    if precio_redondeado > 200000:
        recomendaciones.append(
            "Precio elevado — considera generar una cotización formal con anticipo."
        )

    return {
        "desglose": {
            "tiempo_horas": str(tiempo_horas),
            "costo_por_hora": str(cph.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
            "costo_tiempo": str(costo_tiempo),
            "transporte": str(transporte),
            "desgaste_herramientas": str(desgaste),
            "provision_garantia": str(provision_garantia),
            "costos_directos_total": str(costos_directos_total),
            "costo_total": str(costo_total),
            "margen_aplicado_porcentaje": str(margen),
            "margen_aplicado_monto": str(margen_monto),
            "precio_calculado": str(precio_calculado),
            "precio_redondeado": str(precio_redondeado),
            "precio_con_iva": str(precio_con_iva),
        },
        "parametros_usados": {
            "sueldo_objetivo": str(params.sueldo_objetivo_mensual),
            "costos_fijos": str(params.costos_fijos_mensuales),
            "horas_productivas": str(params.horas_productivas_mensuales),
            "costo_por_hora": str(cph.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        },
        "recomendaciones": recomendaciones,
    }


class CalculoInputSerializer(serializers.Serializer):
    tiempo_horas = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal("0.1"), max_value=Decimal("100")
    )
    transporte = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    desgaste_herramientas = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )
    porcentaje_garantia = serializers.DecimalField(
        max_digits=5, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("100")
    )
    margen_ganancia = serializers.DecimalField(
        max_digits=6, decimal_places=2, min_value=Decimal("0"), max_value=Decimal("500")
    )
    redondear_a = serializers.ChoiceField(choices=REDONDEO_CHOICES, default=0)


class GuardarServicioSerializer(serializers.Serializer):
    codigo = serializers.CharField(max_length=20)
    nombre = serializers.CharField(max_length=200)
    descripcion = serializers.CharField(allow_blank=True, default="")
    datos_calculo = CalculoInputSerializer()
    precio_final = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )


class ActualizarServicioSerializer(serializers.Serializer):
    datos_calculo = CalculoInputSerializer()
    precio_final = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0")
    )


class ParametrosSerializer(serializers.ModelSerializer):
    costo_por_hora = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = ParametrosCalculadora
        fields = [
            "id",
            "sueldo_objetivo_mensual",
            "costos_fijos_mensuales",
            "horas_productivas_mensuales",
            "porcentaje_garantia_default",
            "transporte_base_default",
            "desgaste_herramientas_default",
            "costo_por_hora",
            "fecha_actualizacion",
        ]


class HistorialSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(
        source="usuario.get_full_name", read_only=True
    )
    servicio_codigo = serializers.CharField(
        source="servicio_guardado.code", read_only=True
    )
    servicio_nombre = serializers.CharField(
        source="servicio_guardado.name", read_only=True
    )

    class Meta:
        model = HistorialCalculo
        fields = [
            "id",
            "usuario_nombre",
            "fecha",
            "parametros_input",
            "resultado_calculo",
            "servicio_guardado",
            "servicio_codigo",
            "servicio_nombre",
        ]
