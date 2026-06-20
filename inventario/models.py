from decimal import Decimal

from django.db import models
from django.db.models import Case, F, IntegerField, Sum, When


class ProductCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code_prefix = models.CharField(max_length=4, blank=True)
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


class Brand(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ProductSupplier(models.Model):
    product = models.ForeignKey(
        "Product", on_delete=models.CASCADE, related_name="product_suppliers"
    )
    supplier = models.ForeignKey(
        Supplier, on_delete=models.CASCADE, related_name="product_suppliers"
    )
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    is_preferred = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = [("product", "supplier")]

    def __str__(self):
        return f"{self.product} — {self.supplier}"


class Product(models.Model):
    code = models.CharField(max_length=20, unique=True, blank=True)
    name = models.CharField(max_length=200)
    category = models.ForeignKey(
        ProductCategory, on_delete=models.PROTECT, related_name="products"
    )
    brand = models.ForeignKey(
        "Brand", null=True, blank=True, on_delete=models.SET_NULL, related_name="products"
    )
    model = models.CharField(max_length=100, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2)
    suppliers = models.ManyToManyField(
        Supplier,
        through="ProductSupplier",
        related_name="products",
        blank=True,
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

    def save(self, *args, **kwargs):
        import re
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new and not self.code:
            label = self.category.code_prefix if self.category_id else ''
            if label:
                prefix_str = f'PRD-{label}-'
                existing = (
                    Product.objects
                    .filter(code__startswith=prefix_str)
                    .exclude(pk=self.pk)
                    .values_list('code', flat=True)
                )
                numbers = [
                    int(m.group(1))
                    for c in existing
                    if (m := re.match(r'PRD-\w+-(\d+)$', c))
                ]
                next_num = max(numbers, default=0) + 1
                code = f'PRD-{label}-{next_num:03d}'
            else:
                code = f'PRD-{self.pk:04d}'
            Product.objects.filter(pk=self.pk).update(code=code)
            self.code = code

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
