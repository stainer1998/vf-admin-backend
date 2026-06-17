from decimal import Decimal

from django.db import models
from django.utils import timezone


class WorkOrder(models.Model):
    RECEIVED = "RECEIVED"
    IN_PROGRESS = "IN_PROGRESS"
    READY = "READY"
    DELIVERED = "DELIVERED"
    WORK_STATUS_CHOICES = [
        (RECEIVED, "Received"),
        (IN_PROGRESS, "In Progress"),
        (READY, "Ready"),
        (DELIVERED, "Delivered"),
    ]

    PENDING = "PENDING"
    PAID = "PAID"
    PAYMENT_STATUS_CHOICES = [(PENDING, "Pending"), (PAID, "Paid")]

    TRANSFER = "TRANSFER"
    CASH = "CASH"
    PAYMENT_OTHER = "OTHER"
    PAYMENT_METHOD_CHOICES = [
        (TRANSFER, "Transfer"),
        (CASH, "Cash"),
        (PAYMENT_OTHER, "Other"),
    ]

    client = models.ForeignKey(
        "clientes.Client", on_delete=models.PROTECT, related_name="work_orders"
    )
    equipment = models.ForeignKey(
        "equipos.Equipment", on_delete=models.PROTECT, related_name="work_orders"
    )
    source_quote = models.ForeignKey(
        "cotizaciones.Quote",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="work_orders",
    )
    number = models.CharField(max_length=20, unique=True, blank=True)
    intake_date = models.DateField()
    delivery_date = models.DateField(null=True, blank=True)
    work_status = models.CharField(
        max_length=15, choices=WORK_STATUS_CHOICES, default=RECEIVED
    )
    payment_status = models.CharField(
        max_length=10, choices=PAYMENT_STATUS_CHOICES, default=PENDING
    )
    payment_method = models.CharField(
        max_length=10, choices=PAYMENT_METHOD_CHOICES, blank=True
    )
    adjustment = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0")
    )
    work_description = models.TextField(blank=True)
    notes = models.TextField(blank=True)

    @property
    def amount_charged(self):
        lines_total = sum((line.subtotal for line in self.lines.all()), Decimal("0"))
        return lines_total + self.adjustment

    def save(self, *args, **kwargs):
        if not self.number:
            year = timezone.now().year
            count = WorkOrder.objects.filter(intake_date__year=year).count()
            self.number = f"OT-{year}-{count + 1:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.number} — {self.client} / {self.equipment}"


class WorkOrderLine(models.Model):
    SERVICE = "SERVICE"
    PRODUCT = "PRODUCT"
    TYPE_CHOICES = [(SERVICE, "Service"), (PRODUCT, "Product")]

    work_order = models.ForeignKey(
        WorkOrder, on_delete=models.CASCADE, related_name="lines"
    )
    line_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    service = models.ForeignKey(
        "catalogo.Service", null=True, blank=True, on_delete=models.SET_NULL
    )
    product = models.ForeignKey(
        "inventario.Product", null=True, blank=True, on_delete=models.SET_NULL
    )
    # snapshot — frozen at creation, independent of catalog changes
    description = models.CharField(max_length=300)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveSmallIntegerField(default=1)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=(
                    models.Q(service__isnull=False, product__isnull=True)
                    | models.Q(service__isnull=True, product__isnull=False)
                ),
                name="work_order_line_exactly_one_fk",
            )
        ]

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def __str__(self):
        return f"{self.description} x{self.quantity}"
