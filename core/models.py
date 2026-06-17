from django.db import models
from django.core.exceptions import ValidationError


class AllocationFund(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default="#3B82F6")
    order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    percentage = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.name} ({self.percentage}%)"

    def clean(self):
        total = (
            AllocationFund.objects.filter(is_active=True)
            .exclude(pk=self.pk)
            .aggregate(total=models.Sum("percentage"))["total"]
            or 0
        )
        if self.is_active and total + self.percentage != 100:
            raise ValidationError("Active funds must add up to exactly 100%.")


class DiskInterpretation(models.Model):
    HDD = "HDD"
    SSD = "SSD"
    OTHER = "OTHER"
    DISK_TYPE_CHOICES = [(HDD, "HDD"), (SSD, "SSD"), (OTHER, "Other")]

    pattern = models.CharField(max_length=200, unique=True)
    manufacturer = models.CharField(max_length=100)
    capacity = models.CharField(max_length=20, blank=True)
    rpm = models.PositiveIntegerField(null=True, blank=True)
    disk_type = models.CharField(max_length=10, choices=DISK_TYPE_CHOICES)

    def __str__(self):
        return f"{self.pattern} → {self.manufacturer} {self.capacity}"


class EquipmentLevel(models.Model):
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.name
