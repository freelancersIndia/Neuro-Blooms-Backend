from rest_framework import serializers
from apps.accounts.models.user import User, Role
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip
from apps.accounts.services.email_service import EmailService

class UserAdminSerializer(serializers.ModelSerializer):
    roles = serializers.ListField(child=serializers.CharField(), write_only=True, required=False)
    role_names = serializers.SerializerMethodField(read_only=True)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name', 'last_name',
            'profile_image', 'is_active', 'is_verified', 'password',
            'roles', 'role_names', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_role_names(self, obj) -> list:
        return [role.name for role in obj.roles.all()]

    def create(self, validated_data):
        roles_data = validated_data.pop('roles', [])
        password = validated_data.pop('password', None)

        user = User.objects.create_user(**validated_data)
        if password:
            user.set_password(password)
            user.save()

        for role_name in roles_data:
            role, _ = Role.objects.get_or_create(name=role_name.upper())
            user.roles.add(role)

        request = self.context.get('request')
        ip_address = get_client_ip(request) if request else None

        # Log user creation activity
        ActivityLog.objects.create(
            user=request.user if request and request.user.is_authenticated else None,
            action=ActivityType.USER_CREATED,
            description=f"User account for {user.email} was created.",
            ip_address=ip_address
        )

        # Notify via welcome email
        EmailService.send_account_created(user.email, user.first_name, password)

        return user

    def update(self, instance, validated_data):
        roles_data = validated_data.pop('roles', None)
        password = validated_data.pop('password', None)
        old_is_active = instance.is_active

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        if password:
            instance.set_password(password)

        instance.save()

        if roles_data is not None:
            instance.roles.clear()
            for role_name in roles_data:
                role, _ = Role.objects.get_or_create(name=role_name.upper())
                instance.roles.add(role)

        request = self.context.get('request')
        ip_address = get_client_ip(request) if request else None
        operator = request.user if request and request.user.is_authenticated else None

        # Log update activity
        ActivityLog.objects.create(
            user=operator,
            action=ActivityType.USER_UPDATED,
            description=f"User account for {instance.email} was updated.",
            ip_address=ip_address
        )

        if old_is_active and not instance.is_active:
            # Log deactivation security event
            ActivityLog.objects.create(
                user=operator,
                action=ActivityType.USER_DISABLED,
                description=f"User account for {instance.email} was deactivated/disabled.",
                ip_address=ip_address
            )

        return instance


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'full_name', 'email', 'phone_number', 'profile_image',
            'roles', 'is_verified', 'is_active', 'created_at'
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        # Construct first_name + last_name. Trim whitespace.
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


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    is_locked = serializers.SerializerMethodField()
    failed_login_attempts = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'profile_image',
            'email', 'phone_number', 'roles', 'is_active', 'is_verified',
            'is_locked', 'failed_login_attempts', 'last_login', 'created_at', 'updated_at'
        ]
        read_only_fields = fields

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

    def get_is_locked(self, obj) -> bool:
        from django.utils import timezone
        return obj.locks.filter(is_active=True, unlock_at__gt=timezone.now()).exists()

    def get_failed_login_attempts(self, obj) -> int:
        from apps.accounts.models.user import FailedLoginAttempt
        return FailedLoginAttempt.objects.filter(email=obj.email).count()


class UserUpdateSerializer(serializers.Serializer):
    first_name = serializers.CharField(max_length=150, required=False)
    last_name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    phone_number = serializers.CharField(max_length=20, required=False, allow_null=True, allow_blank=True)
    profile_image = serializers.ImageField(required=False, allow_null=True)
    roles = serializers.ListField(child=serializers.CharField(), required=False)
    is_active = serializers.BooleanField(required=False)
    is_verified = serializers.BooleanField(required=False)

    def validate_email(self, value):
        user = self.instance
        if User.objects.filter(email__iexact=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("User with this email already exists.")
        return value

    def validate_phone_number(self, value):
        if not value:
            return None
        user = self.instance
        if User.objects.filter(phone_number=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("User with this phone number already exists.")
        return value

    def validate_roles(self, value):
        if not value:
            raise serializers.ValidationError("Roles list cannot be empty.")
        
        normalized_roles = [r.upper() for r in value]
        if len(normalized_roles) != len(set(normalized_roles)):
            raise serializers.ValidationError("Duplicate roles are not allowed.")
            
        from apps.accounts.models.user import Role
        invalid_roles = []
        for role_name in normalized_roles:
            if not Role.objects.filter(name=role_name).exists():
                invalid_roles.append(role_name)
        if invalid_roles:
            raise serializers.ValidationError(f"Invalid role: {invalid_roles[0]}")
            
        return normalized_roles

