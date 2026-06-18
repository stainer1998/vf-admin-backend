from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import GroupProfile

User = get_user_model()


# ── Permisos ──────────────────────────────────────────────────────────────────

class PermissionSerializer(serializers.ModelSerializer):
    app_label = serializers.CharField(source="content_type.app_label", read_only=True)
    model     = serializers.CharField(source="content_type.model", read_only=True)

    class Meta:
        model  = Permission
        fields = ["id", "codename", "name", "app_label", "model"]


# ── Grupos ─────────────────────────────────────────────────────────────────────

class GroupSerializer(serializers.ModelSerializer):
    color       = serializers.CharField(default="#6b7280")
    description = serializers.CharField(allow_blank=True, default="")
    is_system   = serializers.SerializerMethodField()
    user_count  = serializers.SerializerMethodField()
    permissions = PermissionSerializer(many=True, read_only=True)
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(),
        many=True,
        write_only=True,
        required=False,
        source="permissions",
    )

    class Meta:
        model  = Group
        fields = [
            "id", "name", "color", "description", "is_system",
            "user_count", "permissions", "permission_ids",
        ]

    def get_is_system(self, obj):
        try:
            return obj.profile.is_system
        except GroupProfile.DoesNotExist:
            return False

    def get_user_count(self, obj):
        return obj.user_set.count()

    def _save_profile(self, group, color, description):
        profile, _ = GroupProfile.objects.get_or_create(group=group)
        if not profile.is_system:
            profile.color       = color
            profile.description = description
            profile.save()
        else:
            # solo actualizar campos que no cambian el estado de sistema
            profile.color       = color
            profile.description = description
            profile.save()

    def create(self, validated_data):
        color       = validated_data.pop("color", "#6b7280")
        description = validated_data.pop("description", "")
        permissions = validated_data.pop("permissions", [])
        group = Group.objects.create(**validated_data)
        GroupProfile.objects.create(group=group, color=color, description=description)
        if permissions:
            group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        color       = validated_data.pop("color", None)
        description = validated_data.pop("description", None)
        permissions = validated_data.pop("permissions", None)
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()
        profile, _ = GroupProfile.objects.get_or_create(group=instance)
        if color is not None:
            profile.color = color
        if description is not None:
            profile.description = description
        profile.save()
        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


class GroupLightSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedding groups inside user responses."""
    color     = serializers.SerializerMethodField()
    is_system = serializers.SerializerMethodField()

    class Meta:
        model  = Group
        fields = ["id", "name", "color", "is_system"]

    def get_color(self, obj):
        try:
            return obj.profile.color
        except GroupProfile.DoesNotExist:
            return "#6b7280"

    def get_is_system(self, obj):
        try:
            return obj.profile.is_system
        except GroupProfile.DoesNotExist:
            return False


# ── Usuarios ──────────────────────────────────────────────────────────────────

class UsuarioSerializer(serializers.ModelSerializer):
    groups           = GroupLightSerializer(many=True, read_only=True)
    user_permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "rol", "is_active", "is_staff", "date_joined", "groups",
            "user_permissions",
        ]
        read_only_fields = ["date_joined"]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    password       = serializers.CharField(write_only=True, min_length=8, required=False, allow_blank=True)
    group_ids      = serializers.PrimaryKeyRelatedField(
        queryset=Group.objects.all(), many=True, write_only=True, required=False, source="groups"
    )
    permission_ids = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, write_only=True, required=False,
        source="user_permissions",
    )

    class Meta:
        model  = User
        fields = [
            "id", "username", "email", "first_name", "last_name",
            "rol", "is_active", "is_staff", "password", "group_ids", "permission_ids",
        ]

    def validate_password(self, value):
        if self.instance is None and not value:
            raise serializers.ValidationError("La contraseña es obligatoria al crear un usuario.")
        return value

    def create(self, validated_data):
        password         = validated_data.pop("password")
        groups           = validated_data.pop("groups", [])
        user_permissions = validated_data.pop("user_permissions", [])
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        if groups:
            user.groups.set(groups)
        if user_permissions:
            user.user_permissions.set(user_permissions)
        return user

    def update(self, instance, validated_data):
        password         = validated_data.pop("password", None)
        groups           = validated_data.pop("groups", None)
        user_permissions = validated_data.pop("user_permissions", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        if user_permissions is not None:
            instance.user_permissions.set(user_permissions)
        return instance


class CambiarPasswordSerializer(serializers.Serializer):
    password_actual = serializers.CharField(write_only=True)
    password_nuevo  = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user
        if not user.check_password(attrs["password_actual"]):
            raise serializers.ValidationError({"password_actual": "Contraseña incorrecta."})
        return attrs


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data["username"]        = self.user.username
        data["rol"]             = self.user.rol
        data["nombre_completo"] = f"{self.user.first_name} {self.user.last_name}".strip()
        return data
