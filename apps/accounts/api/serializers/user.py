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
