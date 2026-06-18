from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import ParametrosCalculadora
from .serializers import CalculoInputSerializer, ejecutar_calculo

User = get_user_model()


def _make_params(user) -> ParametrosCalculadora:
    return ParametrosCalculadora.objects.create(
        sueldo_objetivo_mensual=Decimal("400000"),
        costos_fijos_mensuales=Decimal("150000"),
        horas_productivas_mensuales=Decimal("50"),
        usuario_actualizacion=user,
    )


class CalculoFormulasTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tester", password="x")
        self.params = _make_params(self.user)

    def test_costo_por_hora(self):
        # (400000 + 150000) / 50 = 11000
        self.assertEqual(self.params.costo_por_hora, Decimal("11000"))

    def test_calculo_basico(self):
        resultado = ejecutar_calculo(
            self.params,
            {
                "tiempo_horas": Decimal("1.67"),
                "transporte": Decimal("5000"),
                "desgaste_herramientas": Decimal("500"),
                "porcentaje_garantia": Decimal("5"),
                "margen_ganancia": Decimal("80"),
                "redondear_a": 0,
            },
        )
        desglose = resultado["desglose"]
        self.assertEqual(Decimal(desglose["costo_por_hora"]), Decimal("11000.00"))
        # costo_tiempo = 1.67 * 11000 = 18370
        self.assertEqual(Decimal(desglose["costo_tiempo"]), Decimal("18370.00"))

    def test_calculo_con_redondeo(self):
        resultado = ejecutar_calculo(
            self.params,
            {
                "tiempo_horas": Decimal("1.67"),
                "transporte": Decimal("5000"),
                "desgaste_herramientas": Decimal("500"),
                "porcentaje_garantia": Decimal("5"),
                "margen_ganancia": Decimal("80"),
                "redondear_a": 1000,
            },
        )
        precio_redondeado = Decimal(resultado["desglose"]["precio_redondeado"])
        self.assertEqual(precio_redondeado % 1000, 0)

    def test_precio_con_iva(self):
        resultado = ejecutar_calculo(
            self.params,
            {
                "tiempo_horas": Decimal("1"),
                "transporte": Decimal("0"),
                "desgaste_herramientas": Decimal("0"),
                "porcentaje_garantia": Decimal("0"),
                "margen_ganancia": Decimal("0"),
                "redondear_a": 0,
            },
        )
        precio = Decimal(resultado["desglose"]["precio_redondeado"])
        precio_iva = Decimal(resultado["desglose"]["precio_con_iva"])
        self.assertEqual(precio_iva, (precio * Decimal("1.19")).quantize(Decimal("1")))

    def test_validacion_tiempo_invalido(self):
        serializer = CalculoInputSerializer(
            data={
                "tiempo_horas": "0.05",
                "transporte": "0",
                "desgaste_herramientas": "0",
                "porcentaje_garantia": "5",
                "margen_ganancia": "80",
            }
        )
        self.assertFalse(serializer.is_valid())
        self.assertIn("tiempo_horas", serializer.errors)

    def test_singleton_parametros(self):
        user2 = User.objects.create_user(username="tester2", password="x")
        params2 = ParametrosCalculadora.objects.create(
            sueldo_objetivo_mensual=Decimal("500000"),
            costos_fijos_mensuales=Decimal("100000"),
            horas_productivas_mensuales=Decimal("50"),
            usuario_actualizacion=user2,
        )
        self.params.refresh_from_db()
        params2.refresh_from_db()
        self.assertFalse(self.params.activo)
        self.assertTrue(params2.activo)
