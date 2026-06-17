from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser

from .serializers import UserSerializer

User = get_user_model()


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    search_fields = ["username", "email", "first_name", "last_name"]
    filterset_fields = ["is_active"]
    ordering_fields = ["username", "date_joined"]
    ordering = ["username"]
