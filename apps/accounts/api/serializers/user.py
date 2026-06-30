from rest_framework import serializers
from django.utils import timezone
from apps.accounts.models.user import User, Role, FailedLoginAttempt, AccountLock
from apps.accounts.models.session import UserSession
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
            target_user=user,
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
            target_user=instance,
            action=ActivityType.USER_UPDATED,
            description=f"User account for {instance.email} was updated.",
            ip_address=ip_address
        )

        if old_is_active and not instance.is_active:
            # Log deactivation security event
            ActivityLog.objects.create(
                user=operator,
                target_user=instance,
                action=ActivityType.USER_DISABLED,
                description=f"User account for {instance.email} was deactivated/disabled.",
                ip_address=ip_address
            )

        return instance


class UserListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    roles = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    phone = serializers.CharField(source='phone_number', read_only=True)
    phone_number = serializers.CharField(read_only=True)
    is_locked = serializers.SerializerMethodField()
    failed_login_attempts = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    can_block = serializers.SerializerMethodField()
    can_unlock = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'profile_image', 'full_name', 'email', 'phone', 'phone_number', 'roles',
            'is_verified', 'is_active', 'is_locked', 'failed_login_attempts',
            'last_login', 'created_at', 'updated_at',
            'can_edit', 'can_delete', 'can_block', 'can_unlock'
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
        if hasattr(obj, 'is_locked_annotated'):
            return obj.is_locked_annotated
        return obj.locks.filter(is_active=True, unlock_at__gt=timezone.now()).exists()

    def get_failed_login_attempts(self, obj) -> int:
        if hasattr(obj, 'failed_login_attempts_count'):
            return obj.failed_login_attempts_count
        return FailedLoginAttempt.objects.filter(email=obj.email).count()

    def get_can_edit(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        return True

    def get_can_delete(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.id == request.user.id:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        if obj.is_superuser:
            active_superusers_count = self.context.get('active_superusers_count', 0)
            if active_superusers_count <= 1:
                return False
        if obj.has_role('ADMIN'):
            active_admins_count = self.context.get('active_admins_count', 0)
            if active_admins_count <= 1:
                return False
        return True

    def get_can_block(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.is_blocked:
            return False
        if obj.id == request.user.id:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        if obj.is_superuser:
            active_superusers_count = self.context.get('active_superusers_count', 0)
            if active_superusers_count <= 1:
                return False
        if obj.has_role('ADMIN'):
            active_admins_count = self.context.get('active_admins_count', 0)
            if active_admins_count <= 1:
                return False
        return True

    def get_can_unlock(self, obj) -> bool:
        return bool(obj.is_blocked or self.get_is_locked(obj))


class UserDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    phone = serializers.CharField(source='phone_number', read_only=True)
    phone_number = serializers.CharField(read_only=True)
    roles = serializers.SerializerMethodField()
    blocked = serializers.BooleanField(source='is_blocked', read_only=True)
    locked = serializers.SerializerMethodField()
    active = serializers.BooleanField(source='is_active', read_only=True)
    verified = serializers.BooleanField(source='is_verified', read_only=True)
    failed_login_attempts = serializers.SerializerMethodField()
    created_by = serializers.EmailField(source='created_by.email', read_only=True, default=None)
    updated_by = serializers.EmailField(source='updated_by.email', read_only=True, default=None)
    login_count = serializers.SerializerMethodField()
    last_password_changed = serializers.SerializerMethodField()
    password_expiry = serializers.SerializerMethodField()
    
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    can_block = serializers.SerializerMethodField()
    can_unlock = serializers.SerializerMethodField()
    can_reset_password = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'profile_image', 'first_name', 'last_name', 'full_name',
            'email', 'phone', 'phone_number', 'roles', 'verified', 'blocked', 'locked', 'active',
            'failed_login_attempts', 'last_login', 'created_at', 'updated_at',
            'created_by', 'updated_by', 'login_count', 'last_password_changed', 'password_expiry',
            'can_delete', 'can_edit', 'can_block', 'can_unlock', 'can_reset_password'
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

    def get_locked(self, obj) -> bool:
        if hasattr(obj, 'is_locked_annotated'):
            return obj.is_locked_annotated
        return obj.locks.filter(is_active=True, unlock_at__gt=timezone.now()).exists()

    def get_failed_login_attempts(self, obj) -> int:
        if hasattr(obj, 'failed_login_attempts_count'):
            return obj.failed_login_attempts_count
        return FailedLoginAttempt.objects.filter(email=obj.email).count()

    def get_login_count(self, obj) -> int:
        return ActivityLog.objects.filter(target_user=obj, action=ActivityType.LOGIN).count()

    def get_last_password_changed(self, obj):
        log = ActivityLog.objects.filter(target_user=obj, action=ActivityType.PASSWORD_CHANGED).order_by('-created_at').first()
        return log.created_at if log else None

    def get_password_expiry(self, obj):
        last_changed = self.get_last_password_changed(obj)
        if last_changed:
            return last_changed + timezone.timedelta(days=90)
        return obj.created_at + timezone.timedelta(days=90)

    def get_can_edit(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        return True

    def get_can_delete(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.id == request.user.id:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        if obj.is_superuser:
            active_superusers_count = self.context.get('active_superusers_count', 0)
            if active_superusers_count <= 1:
                return False
        if obj.has_role('ADMIN'):
            active_admins_count = self.context.get('active_admins_count', 0)
            if active_admins_count <= 1:
                return False
        return True

    def get_can_block(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.is_blocked:
            return False
        if obj.id == request.user.id:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        if obj.is_superuser:
            active_superusers_count = self.context.get('active_superusers_count', 0)
            if active_superusers_count <= 1:
                return False
        if obj.has_role('ADMIN'):
            active_admins_count = self.context.get('active_admins_count', 0)
            if active_admins_count <= 1:
                return False
        return True

    def get_can_unlock(self, obj) -> bool:
        return bool(obj.is_blocked or self.get_locked(obj))

    def get_can_reset_password(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.user:
            return False
        if obj.is_superuser and not request.user.is_superuser:
            return False
        return True


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
            
        invalid_roles = []
        for role_name in normalized_roles:
            if not Role.objects.filter(name=role_name).exists():
                invalid_roles.append(role_name)
        if invalid_roles:
            raise serializers.ValidationError(f"Invalid role: {invalid_roles[0]}")
            
        return normalized_roles


class UserSessionSerializer(serializers.ModelSerializer):
    login_time = serializers.DateTimeField(source='login_at', read_only=True)
    current_session = serializers.SerializerMethodField()
    can_revoke = serializers.BooleanField(source='is_active', read_only=True)

    class Meta:
        model = UserSession
        fields = ['id', 'device', 'browser', 'platform', 'ip_address', 'location', 'login_time', 'last_activity', 'current_session', 'can_revoke']
        read_only_fields = fields

    def get_current_session(self, obj) -> bool:
        request = self.context.get('request')
        if not request or not request.auth:
            return False
        jti = request.auth.payload.get('jti') if hasattr(request.auth, 'payload') else None
        return obj.refresh_token_jti == jti


class UserActivityLogSerializer(serializers.ModelSerializer):
    timestamp = serializers.DateTimeField(source='created_at', read_only=True)
    performed_by = serializers.EmailField(source='user.email', read_only=True, default="System")
    ip = serializers.IPAddressField(source='ip_address', read_only=True)

    class Meta:
        model = ActivityLog
        fields = ['timestamp', 'performed_by', 'ip', 'action', 'description']
        read_only_fields = fields
