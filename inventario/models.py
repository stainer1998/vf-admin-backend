from decimal import Decimal

from django.db import models
from django.db.models import Case, F, IntegerField, Sum, When


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_stockable = models.BooleanField(default=True)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "product categories"

    def __str__(self):
        return self.name


class Supplier(models.Model):
    name = models.CharField(max_length=200)
    notes = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Product(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        ProductCategory, on_delete=models.PROTECT, related_name="products"
    )
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    supplier = models.ForeignKey(
        Supplier,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="products",
    )
    notes = models.TextField(blank=True)

    @property
    def margin(self):
        if not self.sale_price:
            return Decimal("0")
        profit = self.sale_price - self.purchase_price
        return (profit / self.sale_price * 100).quantize(Decimal("0.01"))

    @property
    def stock(self):
        result = self.movements.aggregate(
            total=Sum(
                Case(
                    When(movement_type=InventoryMovement.ENTRY, then=F("quantity")),
                    When(movement_type=InventoryMovement.EXIT, then=-F("quantity")),
                    When(movement_type=InventoryMovement.ADJUSTMENT, then=F("quantity")),
                    default=0,
                    output_field=IntegerField(),
                )
            )
        )
        return result["total"] or 0

    def __str__(self):
        return f"{self.code} — {self.name}"


class InventoryMovement(models.Model):
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    ADJUSTMENT = "ADJUSTMENT"
    TYPE_CHOICES = [(ENTRY, "Entry"), (EXIT, "Exit"), (ADJUSTMENT, "Adjustment")]

    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="movements"
    )
    movement_type = models.CharField(max_length=12, choices=TYPE_CHOICES)
    quantity = models.IntegerField()
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField()
    reference = models.CharField(max_length=200, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return (
            f"{self.get_movement_type_display()} {self.quantity}x"
            f" {self.product} ({self.date})"
        )
