from django.contrib.auth import get_user_model
from rest_framework import generics, status, viewsets
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import (
    CambiarPasswordSerializer,
    CustomTokenObtainPairSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)

User = get_user_model()


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAdminUser]
    search_fields = ["username", "email", "first_name", "last_name"]
    filterset_fields = ["is_active", "rol"]
    ordering_fields = ["username", "date_joined"]
    ordering = ["username"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return UsuarioSerializer
        return UsuarioCreateSerializer


class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        return self.request.user


class CambiarPasswordView(generics.GenericAPIView):
    serializer_class = CambiarPasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        request.user.set_password(serializer.validated_data["password_nuevo"])
        request.user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
