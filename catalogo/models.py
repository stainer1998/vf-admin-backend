from decimal import Decimal

from django.db import models


class Service(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    direct_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    @property
    def gross_profit(self):
        return self.sale_price - self.direct_cost

    @property
    def margin(self):
        if not self.sale_price:
            return Decimal("0")
        return (self.gross_profit / self.sale_price * 100).quantize(Decimal("0.01"))

    def __str__(self):
        return f"{self.code} — {self.name}"
