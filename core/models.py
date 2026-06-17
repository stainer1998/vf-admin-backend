from django.db import models
from django.core.exceptions import ValidationError


class FondoReparticion(models.Model):
    nombre = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    descripcion = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")
    orden = models.PositiveSmallIntegerField(default=0)
    activo = models.BooleanField(default=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["orden"]
        verbose_name = "Fondo de Repartición"
        verbose_name_plural = "Fondos de Repartición"

    def __str__(self):
        return f"{self.nombre} ({self.porcentaje}%)"

    def clean(self):
        total = (
            FondoReparticion.objects.filter(activo=True)
            .exclude(pk=self.pk)
            .aggregate(total=models.Sum("porcentaje"))["total"]
            or 0
        )
        if self.activo and total + self.porcentaje != 100:
            raise ValidationError("Los fondos activos deben sumar exactamente 100%.")


class InterpretacionDisco(models.Model):
    patron = models.CharField(max_length=200, unique=True, help_text="Prefijo o regex del modelo crudo")
    fabricante = models.CharField(max_length=100)
    capacidad = models.CharField(max_length=20, blank=True)
    rpm = models.PositiveIntegerField(null=True, blank=True)
    tipo = models.CharField(max_length=10, choices=[("HDD", "HDD"), ("SSD", "SSD"), ("OTRO", "Otro")])

    class Meta:
        verbose_name = "Interpretación de Disco"
        verbose_name_plural = "Interpretaciones de Disco"

    def __str__(self):
        return f"{self.patron} → {self.fabricante} {self.capacidad}"


class NivelEquipo(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden"]
        verbose_name = "Nivel de Equipo"
        verbose_name_plural = "Niveles de Equipo"

    def __str__(self):
        return self.nombre
