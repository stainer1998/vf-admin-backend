from decimal import Decimal

from django.conf import settings
from django.db import models


class ParametrosCalculadora(models.Model):
    """Singleton: solo debe existir un registro activo."""

    sueldo_objetivo_mensual = models.DecimalField(max_digits=12, decimal_places=2)
    costos_fijos_mensuales = models.DecimalField(max_digits=12, decimal_places=2)
    horas_productivas_mensuales = models.DecimalField(
        max_digits=6, decimal_places=2, default=Decimal("50")
    )
    porcentaje_garantia_default = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("5")
    )
    transporte_base_default = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("5000")
    )
    desgaste_herramientas_default = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("500")
    )
    activo = models.BooleanField(default=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_actualizacion = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = "Parámetros de Calculadora"
        verbose_name_plural = "Parámetros de Calculadora"

    @property
    def costo_por_hora(self) -> Decimal:
        return (
            self.sueldo_objetivo_mensual + self.costos_fijos_mensuales
        ) / self.horas_productivas_mensuales

    def save(self, *args, **kwargs):
        if self.activo:
            ParametrosCalculadora.objects.filter(activo=True).exclude(pk=self.pk).update(
                activo=False
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Parámetros (costo/hora: ${self.costo_por_hora:,.0f})"


class HistorialCalculo(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)
    parametros_input = models.JSONField()
    resultado_calculo = models.JSONField()
    servicio_guardado = models.ForeignKey(
        "catalogo.Service",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="calculos_origen",
    )

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Historial de Cálculo"
        verbose_name_plural = "Historial de Cálculos"

    def __str__(self):
        return f"Cálculo {self.pk} — {self.usuario} — {self.fecha:%Y-%m-%d %H:%M}"
