from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CambiarPasswordView,
    GroupViewSet,
    MeView,
    PermissionListView,
    UsuarioViewSet,
)

router = DefaultRouter()
router.register("users", UsuarioViewSet, basename="user")
router.register("groups", GroupViewSet, basename="group")

urlpatterns = router.urls + [
    path("me/", MeView.as_view(), name="me"),
    path("me/cambiar-password/", CambiarPasswordView.as_view(), name="cambiar-password"),
    path("permissions/", PermissionListView.as_view(), name="permissions"),
]
