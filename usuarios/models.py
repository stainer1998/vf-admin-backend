from django.contrib.auth.models import AbstractUser
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
