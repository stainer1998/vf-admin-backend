from rest_framework import serializers
from .models import FondoReparticion, InterpretacionDisco, NivelEquipo


class FondoReparticionSerializer(serializers.ModelSerializer):
    class Meta:
        model = FondoReparticion
        fields = "__all__"


class InterpretacionDiscoSerializer(serializers.ModelSerializer):
    class Meta:
        model = InterpretacionDisco
        fields = "__all__"


class NivelEquipoSerializer(serializers.ModelSerializer):
    class Meta:
        model = NivelEquipo
        fields = "__all__"
