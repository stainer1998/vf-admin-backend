from decimal import Decimal

from django.db import models


class Service(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2)
    direct_cost = models.DecimalField(
        max_digits=12, decimal_places=2, default=Decimal("0")
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
    metadata_calculo = models.JSONField(null=True, blank=True)

    @property
    def gross_profit(self):
        return self.sale_price - self.direct_cost

    @property
    def margin(self):
        if not self.direct_cost:
            return None
        return (self.gross_profit / self.direct_cost * 100).quantize(Decimal("0.01"))

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.code:
            code = f'SRV-{self.pk:04d}'
            Service.objects.filter(pk=self.pk).update(code=code)
            self.code = code

    def __str__(self):
        return f"{self.code} — {self.name}"


class ServiceMaterial(models.Model):
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="materials"
    )
    product = models.ForeignKey(
        "inventario.Product", on_delete=models.CASCADE, related_name="service_materials"
    )
    default_quantity = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = [("service", "product")]

    def __str__(self):
        return f"{self.service.code} → {self.product.code} ×{self.default_quantity}"


class ServiceRequiredCategory(models.Model):
    """
    Vincula un servicio con una categoría de producto, para que al usar el
    servicio en una OT o cotización el técnico seleccione el insumo concreto
    de esa categoría. Si billable=False el insumo es consumible interno y no
    se agrega como línea de cobro al cliente.
    """

    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name="required_categories"
    )
    category = models.ForeignKey(
        "inventario.ProductCategory",
        on_delete=models.PROTECT,
        related_name="service_requirements",
    )
    label = models.CharField(max_length=100, blank=True)
    billable = models.BooleanField(default=True)
    default_quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        unique_together = [("service", "category")]
        ordering = ["-billable", "label"]

    def __str__(self):
        tag = "billable" if self.billable else "interno"
        return f"{self.service.code} → {self.category.name} ({tag})"
