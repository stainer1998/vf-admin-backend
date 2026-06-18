from django.contrib import admin

from .models import HistorialCalculo, ParametrosCalculadora


@admin.register(ParametrosCalculadora)
class ParametrosCalculadoraAdmin(admin.ModelAdmin):
    list_display = [
        "sueldo_objetivo_mensual",
        "costos_fijos_mensuales",
        "horas_productivas_mensuales",
        "costo_por_hora_display",
        "activo",
        "fecha_actualizacion",
        "usuario_actualizacion",
    ]
    readonly_fields = ["costo_por_hora_display", "fecha_actualizacion"]

    @admin.display(description="Costo por hora")
    def costo_por_hora_display(self, obj):
        return f"${obj.costo_por_hora:,.0f}"

    def save_model(self, request, obj, form, change):
        obj.usuario_actualizacion = request.user
        super().save_model(request, obj, form, change)


@admin.register(HistorialCalculo)
class HistorialCalculoAdmin(admin.ModelAdmin):
    list_display = ["pk", "usuario", "fecha", "servicio_guardado"]
    list_filter = ["fecha", "usuario"]
    readonly_fields = ["usuario", "fecha", "parametros_input", "resultado_calculo", "servicio_guardado"]
    ordering = ["-fecha"]
