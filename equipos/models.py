from django.db import models
from vf_core.normalize import normalize


class Equipment(models.Model):
    NOTEBOOK = "NOTEBOOK"
    DESKTOP = "DESKTOP"
    AIO = "AIO"
    MINIPC = "MINIPC"
    TYPE_CHOICES = [
        (NOTEBOOK, "Notebook"),
        (DESKTOP, "Desktop"),
        (AIO, "All-in-One"),
        (MINIPC, "Mini PC"),
    ]

    BRAND = "BRAND"
    ASSEMBLED = "ASSEMBLED"
    DESKTOP_SUBTYPE_CHOICES = [(BRAND, "Brand"), (ASSEMBLED, "Assembled")]

    client = models.ForeignKey(
        "clientes.Client", on_delete=models.PROTECT, related_name="equipment"
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    desktop_subtype = models.CharField(
        max_length=10, choices=DESKTOP_SUBTYPE_CHOICES, blank=True
    )
    brand = models.CharField(max_length=100)
    model = models.CharField(max_length=200)
    serial_number = models.CharField(max_length=200, blank=True)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    identity_key = models.CharField(max_length=200, unique=True, db_index=True)
    is_ambiguous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _compute_identity_key(self):
        if self.serial_number:
            self.is_ambiguous = False
            return normalize(self.serial_number)
        self.is_ambiguous = True
        return normalize(f"{self.brand} {self.model}")

    def save(self, *args, **kwargs):
        self.identity_key = self._compute_identity_key()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.brand} {self.model} ({self.get_type_display()})"
