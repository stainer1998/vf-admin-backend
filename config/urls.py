from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import TokenRefreshView
from usuarios.views import CustomTokenObtainPairView

urlpatterns = [
    path("admin/", admin.site.urls),
    # JWT
    path("api/auth/token/", CustomTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    # OpenAPI docs
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    # Apps
    path("api/", include("core.urls")),
    path("api/", include("clientes.urls")),
    path("api/", include("equipos.urls")),
    path("api/", include("catalogo.urls")),
    path("api/", include("inventario.urls")),
    path("api/", include("cotizaciones.urls")),
    path("api/", include("trabajos.urls")),
    path("api/", include("finanzas.urls")),
    path("api/", include("diagnosticos.urls")),
    path("api/admin/", include("usuarios.urls")),
]
