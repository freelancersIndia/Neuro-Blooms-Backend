from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password as django_validate_password
from apps.accounts.models.user import Role

User = get_user_model()

class CreateUserSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=True)
    last_name = serializers.CharField(max_length=150, required=True)
    email = serializers.EmailField(required=True)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True, default=None)
    profile_image = serializers.ImageField(required=False, allow_null=True, default=None)
    password = serializers.CharField(max_length=128, required=True, write_only=True)
    roles = serializers.ListField(child=serializers.CharField(), required=True)
    is_active = serializers.BooleanField(required=False, default=True)
    is_verified = serializers.BooleanField(required=False, default=False)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if not value:
            return None
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("User with this phone number already exists.")
        return value

    def validate_password(self, value):
        if len(value) < 8:
            raise serializers.ValidationError("Password must be at least 8 characters long.")
        try:
            # Validate password using Django validators
            django_validate_password(value)
        except Exception as e:
            if hasattr(e, 'messages'):
                raise serializers.ValidationError(e.messages)
            else:
                raise serializers.ValidationError(str(e))
        return value

    def validate_roles(self, value):
        if not value:
            raise serializers.ValidationError("Roles list cannot be empty.")

        normalized_roles = [r.upper() for r in value]

        # Prevent duplicate roles
        if len(normalized_roles) != len(set(normalized_roles)):
            raise serializers.ValidationError("Duplicate roles are not allowed.")

        # Check every role exists
        invalid_roles = []
        for role_name in normalized_roles:
            if not Role.objects.filter(name=role_name).exists():
                invalid_roles.append(role_name)

        if invalid_roles:
            raise serializers.ValidationError(f"Invalid role: {invalid_roles[0]}")

        return normalized_roles


class CreatedUserResponseSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone_number',
            'profile_image', 'roles', 'is_active', 'is_verified', 'created_at'
        ]

    def get_full_name(self, obj) -> str:
        first = obj.first_name or ""
        last = obj.last_name or ""
        return f"{first} {last}".strip()

    def get_roles(self, obj) -> list:
        return [role.name for role in obj.roles.all()]

    def get_profile_image(self, obj) -> str:
        if not obj.profile_image:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url
