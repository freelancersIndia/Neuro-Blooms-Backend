from rest_framework import serializers
from django.core.paginator import Paginator
from django.contrib.auth import get_user_model
from apps.accounts.models import Role, Permission, UserRole
from apps.accounts.api.serializers.permission import PermissionSerializer

User = get_user_model()

class RolePermissionSerializer(serializers.ModelSerializer):
    assigned = serializers.SerializerMethodField()

    class Meta:
        model = Permission
        fields = ['id', 'name', 'code', 'group', 'description', 'assigned']

    def get_assigned(self, obj):
        assigned_ids = self.context.get('assigned_permission_ids', set())
        return obj.id in assigned_ids


class RoleListSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)
    permissions_count = serializers.IntegerField(read_only=True)
    can_delete = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'users_count', 'permissions_count',
            'is_system', 'is_active', 'created_at', 'updated_at', 'can_delete', 'can_edit'
        ]

    def get_can_delete(self, obj):
        # A role cannot be deleted if it is a system role or has users assigned
        users_count = getattr(obj, 'users_count', 0)
        return not obj.is_system and users_count == 0

    def get_can_edit(self, obj):
        # System roles can be edited (e.g. description/permissions), but name cannot be changed.
        # So editing is allowed, but we enforce name protection in validation.
        return True


class RoleDetailSerializer(serializers.ModelSerializer):
    users_count = serializers.IntegerField(read_only=True)
    permissions_count = serializers.IntegerField(read_only=True)
    created_by = serializers.SerializerMethodField()
    updated_by = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()
    assigned_users = serializers.SerializerMethodField()

    class Meta:
        model = Role
        fields = [
            'id', 'name', 'description', 'is_system', 'is_active',
            'created_at', 'updated_at', 'created_by', 'updated_by',
            'users_count', 'permissions_count', 'permissions', 'assigned_users'
        ]

    def get_created_by(self, obj):
        return obj.created_by.email if obj.created_by else 'System'

    def get_updated_by(self, obj):
        return obj.updated_by.email if obj.updated_by else 'System'

    def get_permissions(self, obj):
        all_perms = Permission.objects.all()
        assigned_ids = set(obj.permissions.values_list('id', flat=True))
        return RolePermissionSerializer(
            all_perms,
            many=True,
            context={'assigned_permission_ids': assigned_ids}
        ).data

    def get_assigned_users(self, obj):
        request = self.context.get('request')
        users_qs = obj.users.all().order_by('first_name', 'last_name')

        # Pagination params
        page_num = 1
        page_size = 10
        if request:
            page_num = request.query_params.get('user_page', 1)
            page_size = request.query_params.get('user_page_size', 10)

        paginator = Paginator(users_qs, page_size)
        try:
            page = paginator.page(page_num)
        except Exception:
            page = paginator.page(1)

        class AssignedUserSerializer(serializers.ModelSerializer):
            full_name = serializers.SerializerMethodField()
            phone = serializers.CharField(source='phone_number')
            status = serializers.SerializerMethodField()
            can_remove = serializers.SerializerMethodField()

            class Meta:
                model = User
                fields = ['id', 'profile_image', 'full_name', 'email', 'phone', 'status', 'last_login', 'can_remove']

            def get_full_name(self, user_obj):
                return f"{user_obj.first_name} {user_obj.last_name}".strip() or user_obj.email

            def get_status(self, user_obj):
                return "Active" if user_obj.is_active else "Inactive"

            def get_can_remove(self, user_obj):
                # Cannot remove the last user from the ADMIN role
                if obj.name == 'ADMIN':
                    admin_users_count = UserRole.objects.filter(role__name='ADMIN').count()
                    if admin_users_count <= 1:
                        return False
                return True

        results = AssignedUserSerializer(page.object_list, many=True).data

        base_url = request.build_absolute_uri(request.path) if request else ''
        next_link = None
        if page.has_next():
            next_link = f"{base_url}?user_page={page.next_page_number()}&user_page_size={page_size}"
        prev_link = None
        if page.has_previous():
            prev_link = f"{base_url}?user_page={page.previous_page_number()}&user_page_size={page_size}"

        return {
            'count': paginator.count,
            'page': page.number,
            'page_size': int(page_size),
            'total_pages': paginator.num_pages,
            'next': next_link,
            'previous': prev_link,
            'results': results
        }


class RoleCreateUpdateSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Permission.objects.all(), required=True
    )

    class Meta:
        model = Role
        fields = ['name', 'description', 'is_active', 'permissions']

    def validate_name(self, value):
        # Case-insensitive uniqueness check (excluding self if updating)
        queryset = Role.objects.filter(name__iexact=value, is_deleted=False)
        if self.instance:
            queryset = queryset.exclude(id=self.instance.id)
        if queryset.exists():
            raise serializers.ValidationError("A role with this name already exists.")
        
        if len(value) < 3 or len(value) > 50:
            raise serializers.ValidationError("Role name must be between 3 and 50 characters.")
        return value

    def validate_description(self, value):
        if value and len(value) > 500:
            raise serializers.ValidationError("Description cannot exceed 500 characters.")
        return value

    def validate_permissions(self, value):
        if not value:
            raise serializers.ValidationError("A role must have at least one permission.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.is_system:
            if 'name' in attrs and attrs['name'] != self.instance.name:
                raise serializers.ValidationError({"name": "System role names cannot be modified."})
            if 'is_active' in attrs and not attrs['is_active'] and self.instance.name == 'ADMIN':
                raise serializers.ValidationError({"is_active": "The ADMIN system role cannot be deactivated."})
        return attrs
