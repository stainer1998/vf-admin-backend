from django.contrib.auth.models import AbstractUser, Group
from django.db import models


class UsuarioVF(AbstractUser):
    class Rol(models.TextChoices):
        ADMIN    = "ADMIN",    "Administrador"
        TECNICO  = "TECNICO",  "Técnico"
        VENDEDOR = "VENDEDOR", "Vendedor"

    rol = models.CharField(max_length=10, choices=Rol.choices, default=Rol.TECNICO)

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["username"]


class GroupProfile(models.Model):
    group       = models.OneToOneField(Group, on_delete=models.CASCADE, related_name="profile")
    color       = models.CharField(max_length=7, default="#6b7280")
    description = models.TextField(blank=True)
    is_system   = models.BooleanField(default=False)

    class Meta:
        verbose_name = "perfil de grupo"
        verbose_name_plural = "perfiles de grupo"
