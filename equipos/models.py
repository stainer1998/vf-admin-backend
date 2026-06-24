from django.db import models
from django.utils import timezone
from vf_core.normalize import normalize


class EquipmentManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


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
    color = models.CharField(max_length=50, blank=True)
    specifications = models.JSONField(default=dict, blank=True)
    identity_key = models.CharField(max_length=200, unique=True, db_index=True)
    is_ambiguous = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = EquipmentManager()
    all_objects = models.Manager()

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

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
