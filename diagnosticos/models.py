import hashlib
import json

from django.conf import settings
from django.db import models


class Diagnosis(models.Model):
    LOOKOUT = "LOOKOUT"
    MOBILE_APP = "MOBILE_APP"
    WEB = "WEB"
    INGRESS_SOURCE_CHOICES = [
        (LOOKOUT, "Lookout"),
        (MOBILE_APP, "Mobile App"),
        (WEB, "Web"),
    ]

    equipment = models.ForeignKey(
        "equipos.Equipment", on_delete=models.PROTECT, related_name="diagnoses"
    )
    timestamp = models.DateTimeField()
    source_file = models.CharField(max_length=500, blank=True)
    schema_version = models.CharField(max_length=20)
    raw_json = models.JSONField()
    ingress_source = models.CharField(
        max_length=15, choices=INGRESS_SOURCE_CHOICES, default=LOOKOUT
    )
    content_hash = models.CharField(max_length=64, unique=True)
    imported_at = models.DateTimeField(auto_now_add=True)
    imported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="imported_diagnoses",
    )

    class Meta:
        ordering = ["-timestamp"]
        verbose_name_plural = "diagnoses"

    def save(self, *args, **kwargs):
        self.content_hash = hashlib.sha256(
            json.dumps(self.raw_json, sort_keys=True).encode()
        ).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Diagnosis {self.pk} — {self.equipment} ({self.timestamp:%Y-%m-%d})"


class DetectedSpecification(models.Model):
    diagnosis = models.OneToOneField(
        Diagnosis, on_delete=models.CASCADE, related_name="specification"
    )
    os_name = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    cpu_model = models.CharField(max_length=200, blank=True)
    ram_total_gb = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    gpu_model = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Specs for {self.diagnosis}"


class StorageDevice(models.Model):
    INTERNAL_DISK = "INTERNAL_DISK"
    OPTICAL_DRIVE = "OPTICAL_DRIVE"
    CATEGORY_CHOICES = [
        (INTERNAL_DISK, "Internal Disk"),
        (OPTICAL_DRIVE, "Optical Drive"),
    ]

    HDD = "HDD"
    SSD = "SSD"
    DISK_OTHER = "OTHER"
    DISK_TYPE_CHOICES = [(HDD, "HDD"), (SSD, "SSD"), (DISK_OTHER, "Other")]

    SATA = "SATA"
    NVME = "NVME"
    IDE = "IDE"
    USB = "USB"
    INTERFACE_OTHER = "OTHER"
    INTERFACE_CHOICES = [
        (SATA, "SATA"),
        (NVME, "NVMe"),
        (IDE, "IDE"),
        (USB, "USB"),
        (INTERFACE_OTHER, "Other"),
    ]

    diagnosis = models.ForeignKey(
        Diagnosis, on_delete=models.CASCADE, related_name="storage_devices"
    )
    category = models.CharField(max_length=15, choices=CATEGORY_CHOICES)
    disk_type = models.CharField(max_length=10, choices=DISK_TYPE_CHOICES, blank=True)
    interface = models.CharField(max_length=10, choices=INTERFACE_CHOICES, blank=True)
    capacity_gb = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    raw_model = models.CharField(max_length=300)

    def __str__(self):
        return f"{self.raw_model} ({self.get_category_display()})"


class ManualCorrection(models.Model):
    diagnosis = models.ForeignKey(
        Diagnosis, on_delete=models.CASCADE, related_name="corrections"
    )
    field = models.CharField(max_length=100)
    value = models.TextField()
    corrected_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="manual_corrections",
    )
    corrected_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Correction on {self.diagnosis}: {self.field}"
