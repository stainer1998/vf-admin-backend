from decimal import Decimal

from django.db import models
from django.utils import timezone


def _next_folio(prefix, model_class):
    year = timezone.now().year
    count = model_class.objects.filter(date__year=year).count()
    return f"{prefix}-{year}-{count + 1:04d}"


class Quote(models.Model):
    DRAFT = "DRAFT"
    SENT = "SENT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (SENT, "Sent"),
        (APPROVED, "Approved"),
        (REJECTED, "Rejected"),
        (EXPIRED, "Expired"),
    ]

    client = models.ForeignKey(
        "clientes.Client", on_delete=models.PROTECT, related_name="quotes"
    )
    equipment = models.ForeignKey(
        "equipos.Equipment",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quotes",
    )
    source_diagnosis = models.ForeignKey(
        "diagnosticos.Diagnosis",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="quotes",
    )
    folio = models.CharField(max_length=20, unique=True, blank=True)
    date = models.DateField()
    validity_days = models.PositiveSmallIntegerField(default=15)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=DRAFT)
    iva = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    notes = models.TextField(blank=True)

    @property
    def subtotal(self):
        return sum((line.subtotal for line in self.lines.all()), Decimal("0"))

    @property
    def total(self):
        return self.subtotal + self.iva

    def save(self, *args, **kwargs):
        if not self.folio:
            self.folio = _next_folio("COT", Quote)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.folio} — {self.client}"


class QuoteLine(models.Model):
    SERVICE = "SERVICE"
    PRODUCT = "PRODUCT"
    TYPE_CHOICES = [(SERVICE, "Service"), (PRODUCT, "Product")]

    quote = models.ForeignKey(Quote, on_delete=models.CASCADE, related_name="lines")
    line_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    service = models.ForeignKey(
        "catalogo.Service", null=True, blank=True, on_delete=models.SET_NULL
    )
    product = models.ForeignKey(
        "inventario.Product", null=True, blank=True, on_delete=models.SET_NULL
    )
    # snapshot — frozen at creation, independent of catalog changes
    description = models.CharField(max_length=300)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(service__isnull=False, product__isnull=True)
                    | models.Q(service__isnull=True, product__isnull=False)
                ),
                name="quote_line_exactly_one_fk",
            )
        ]

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.description} x{self.quantity}"
