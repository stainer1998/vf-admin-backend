from django.db import models
from vf_core.normalize import normalize


class Client(models.Model):
    PERSON = "PERSON"
    COMPANY = "COMPANY"
    TYPE_CHOICES = [(PERSON, "Person"), (COMPANY, "Company")]

    LOOKOUT = "LOOKOUT"
    MANUAL = "MANUAL"
    SOURCE_CHOICES = [(LOOKOUT, "Lookout"), (MANUAL, "Manual")]

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    second_last_name = models.CharField(max_length=100, blank=True)
    identity_key = models.CharField(max_length=200, unique=True, db_index=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    rut = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    merged_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="absorbed_clients",
    )
    source = models.CharField(max_length=10, choices=SOURCE_CHOICES, default=MANUAL)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def _compute_identity_key(self):
        if self.type == self.COMPANY:
            return self.rut.strip() if self.rut else normalize(self.company_name)
        return normalize(f"{self.first_name} {self.last_name} {self.second_last_name}")

    def save(self, *args, **kwargs):
        self.identity_key = self._compute_identity_key()
        super().save(*args, **kwargs)

    def __str__(self):
        if self.type == self.COMPANY:
            return self.company_name or self.first_name
        return f"{self.first_name} {self.last_name}".strip()
