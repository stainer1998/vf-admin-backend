from django.urls import path

from .views import (
    ActualizarServicioView,
    CalcularView,
    GuardarComoServicioView,
    HistorialView,
    ParametrosView,
)

urlpatterns = [
    path("calculadora/parametros/", ParametrosView.as_view()),
    path("calculadora/calcular/", CalcularView.as_view()),
    path("calculadora/guardar-como-servicio/", GuardarComoServicioView.as_view()),
    path("calculadora/actualizar-servicio/<int:pk>/", ActualizarServicioView.as_view()),
    path("calculadora/historial/", HistorialView.as_view()),
]
