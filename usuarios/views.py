from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.db import models
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import GroupProfile
from .serializers import (
    CambiarPasswordSerializer,
    CustomTokenObtainPairSerializer,
    GroupSerializer,
    PermissionSerializer,
    UsuarioCreateSerializer,
    UsuarioSerializer,
)

User = get_user_model()

VF_APPS = [
    "clientes", "equipos", "diagnosticos", "catalogo",
    "inventario", "cotizaciones", "trabajos", "finanzas", "core", "usuarios",
]


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = User.objects.prefetch_related("groups__profile", "user_permissions__content_type").all()
    permission_classes = [IsAdminUser]
    search_fields = ["username", "email", "first_name", "last_name"]
    filterset_fields = ["is_active", "rol"]
    ordering_fields = ["username", "date_joined"]
    ordering = ["username"]

    def get_serializer_class(self):
        if self.action in ("list", "retrieve"):
            return UsuarioSerializer
        return UsuarioCreateSerializer

    @action(detail=True, methods=["get"], url_path="effective-permissions")
    def effective_permissions(self, request, pk=None):
        user = self.get_object()
        perms = (
            Permission.objects.select_related("content_type")
            .filter(content_type__app_label__in=VF_APPS)
            .filter(
                models.Q(user=user) | models.Q(group__user=user)
            )
            .distinct()
            .order_by("content_type__app_label", "content_type__model", "codename")
        )
        return Response(PermissionSerializer(perms, many=True).data)


class GroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.prefetch_related("profile", "permissions__content_type").all()
    serializer_class = GroupSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None
    ordering = ["name"]

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            if instance.profile.is_system:
                return Response(
                    {"detail": "No se puede eliminar un grupo del sistema."},
                    status=status.HTTP_403_FORBIDDEN,
                )
        except GroupProfile.DoesNotExist:
            pass
        return super().destroy(request, *args, **kwargs)


class PermissionListView(generics.ListAPIView):
    serializer_class = PermissionSerializer
    permission_classes = [IsAdminUser]
    pagination_class = None

    def get_queryset(self):
        return (
            Permission.objects.select_related("content_type")
            .filter(content_type__app_label__in=VF_APPS)
            .order_by("content_type__app_label", "content_type__model", "codename")
        )


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
