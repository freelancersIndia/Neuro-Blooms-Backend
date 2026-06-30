from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models import Role, Permission, UserRole, User
from apps.accounts.api.serializers import RoleListSerializer, RoleDetailSerializer, RoleCreateUpdateSerializer
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.api.pagination import RolePagination

class RoleViewSet(viewsets.ModelViewSet):
    """
    Role Management ViewSet for Administrators.
    Provides listing, detail, creation, update, soft-deletion, and quick actions
    for managing role-permission and role-user mappings.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    pagination_class = RolePagination
    lookup_field = 'id'

    def get_queryset(self):
        queryset = Role.objects.filter(is_deleted=False).annotate(
            users_count=Count('users', distinct=True),
            permissions_count=Count('permissions', distinct=True)
        ).select_related('created_by', 'updated_by')

        # 1. Search (matches name and description, case-insensitive)
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))

        # 2. Filters
        # Status Filter
        status_param = self.request.query_params.get('status')
        if status_param:
            if status_param.lower() == 'active':
                queryset = queryset.filter(is_active=True)
            elif status_param.lower() == 'inactive':
                queryset = queryset.filter(is_active=False)

        # Role Type Filter (System vs Custom)
        type_param = self.request.query_params.get('type')
        if type_param:
            if type_param.lower() == 'system':
                queryset = queryset.filter(is_system=True)
            elif type_param.lower() == 'custom':
                queryset = queryset.filter(is_system=False)

        # Date Filters
        created_after = self.request.query_params.get('created_after')
        created_before = self.request.query_params.get('created_before')
        if created_after:
            queryset = queryset.filter(created_at__gte=created_after)
        if created_before:
            queryset = queryset.filter(created_at__lte=created_before)

        # Shortcut Date Filters
        date_range = self.request.query_params.get('date_range')
        if date_range:
            today = timezone.now().date()
            if date_range == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif date_range == '7_days':
                queryset = queryset.filter(created_at__date__gte=today - timedelta(days=7))
            elif date_range == '30_days':
                queryset = queryset.filter(created_at__date__gte=today - timedelta(days=30))

        # User Count Filter (Empty Roles vs Roles with Users)
        has_users = self.request.query_params.get('has_users')
        if has_users is not None:
            if has_users.lower() == 'true':
                queryset = queryset.filter(users_count__gt=0)
            elif has_users.lower() == 'false':
                queryset = queryset.filter(users_count=0)

        # 3. Ordering
        ordering = self.request.query_params.get('ordering')
        if ordering:
            valid_orderings = {
                'name': 'name',
                '-name': '-name',
                'created_at': 'created_at',
                '-created_at': '-created_at',
                'users_count': 'users_count',
                '-users_count': '-users_count',
                'permissions_count': 'permissions_count',
                '-permissions_count': '-permissions_count'
            }
            if ordering in valid_orderings:
                queryset = queryset.order_by(valid_orderings[ordering])
        else:
            queryset = queryset.order_by('-created_at')

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return RoleListSerializer
        elif self.action == 'retrieve':
            return RoleDetailSerializer
        elif self.action in ['create', 'update', 'partial_update']:
            return RoleCreateUpdateSerializer
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user, updated_by=self.request.user)

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Fetch the created role with annotations for response consistency
        instance = self.get_queryset().get(name__iexact=serializer.validated_data['name'])
        response_serializer = RoleDetailSerializer(instance, context={'request': request})
        return success_response(
            message="Role created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Re-fetch with annotations
        instance = self.get_queryset().get(id=instance.id)
        response_serializer = RoleDetailSerializer(instance, context={'request': request})
        return success_response(
            message="Role updated successfully.",
            data=response_serializer.data
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            message="Role details retrieved successfully.",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        users_count = instance.users.count()

        if instance.is_system:
            return error_response(
                message="System roles cannot be deleted.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        if users_count > 0:
            return error_response(
                message="Cannot delete role with assigned users.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        
        # Soft delete
        instance.is_deleted = True
        instance.save()
        return success_response(
            message="Role deleted successfully.",
            data=None
        )

    @action(detail=False, methods=['get'], url_path='dropdown')
    def dropdown(self, request):
        """
        Returns only active roles for dropdown selection.
        """
        roles = Role.objects.filter(is_deleted=False, is_active=True).order_by('name')
        data = [{"id": str(role.id), "name": role.name} for role in roles]
        return success_response(
            message="Active roles retrieved successfully.",
            data=data
        )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Calculates role statistics for the dashboard.
        """
        roles_qs = Role.objects.filter(is_deleted=False)
        total_roles = roles_qs.count()
        active_roles = roles_qs.filter(is_active=True).count()
        inactive_roles = roles_qs.filter(is_active=False).count()
        system_roles = roles_qs.filter(is_system=True).count()
        custom_roles = roles_qs.filter(is_system=False).count()
        
        total_assigned_users = UserRole.objects.filter(role__is_deleted=False).values('user').distinct().count()

        data = {
            "total_roles": total_roles,
            "active_roles": active_roles,
            "inactive_roles": inactive_roles,
            "system_roles": system_roles,
            "custom_roles": custom_roles,
            "total_assigned_users": total_assigned_users
        }
        return success_response(
            message="Role statistics retrieved successfully.",
            data=data
        )

    @action(detail=True, methods=['post'], url_path='permissions/assign')
    def assign_permissions(self, request, id=None):
        """
        Assigns one or more permissions to the role.
        """
        role = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        if not isinstance(permission_ids, list) or not permission_ids:
            return error_response(
                message="permission_ids must be a non-empty list.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        permissions = Permission.objects.filter(id__in=permission_ids)
        if permissions.count() != len(set(permission_ids)):
            return error_response(
                message="One or more permission IDs are invalid.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            role.permissions.add(*permissions)
            role.save()

        return success_response(message="Permissions assigned successfully.")

    @action(detail=True, methods=['post'], url_path='permissions/remove')
    def remove_permissions(self, request, id=None):
        """
        Removes one or more permissions from the role.
        """
        role = self.get_object()
        permission_ids = request.data.get('permission_ids', [])
        if not isinstance(permission_ids, list) or not permission_ids:
            return error_response(
                message="permission_ids must be a non-empty list.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        permissions = Permission.objects.filter(id__in=permission_ids)
        if permissions.count() != len(set(permission_ids)):
            return error_response(
                message="One or more permission IDs are invalid.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validation: Cannot remove required permissions from the ADMIN system role
        if role.name == 'ADMIN':
            return error_response(
                message="Cannot remove permissions from the ADMIN system role.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            role.permissions.remove(*permissions)
            role.save()

        return success_response(message="Permissions removed successfully.")

    @action(detail=True, methods=['post'], url_path='users/assign')
    def assign_users(self, request, id=None):
        """
        Assigns one or more users to the role.
        """
        role = self.get_object()
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return error_response(
                message="user_ids must be a non-empty list.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(id__in=user_ids)
        if users.count() != len(set(user_ids)):
            return error_response(
                message="One or more user IDs are invalid.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            for user in users:
                UserRole.objects.get_or_create(user=user, role=role)

        return success_response(message="Users assigned to role successfully.")

    @action(detail=True, methods=['post'], url_path='users/remove')
    def remove_users(self, request, id=None):
        """
        Removes one or more users from the role.
        """
        role = self.get_object()
        user_ids = request.data.get('user_ids', [])
        if not isinstance(user_ids, list) or not user_ids:
            return error_response(
                message="user_ids must be a non-empty list.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        users = User.objects.filter(id__in=user_ids)
        if users.count() != len(set(user_ids)):
            return error_response(
                message="One or more user IDs are invalid.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Validation: Cannot remove the last user from the ADMIN role
        if role.name == 'ADMIN':
            admin_users_count = UserRole.objects.filter(role=role).count()
            removing_admin_count = UserRole.objects.filter(role=role, user__in=users).count()
            if admin_users_count - removing_admin_count < 1:
                return error_response(
                    message="Cannot remove the last user from the ADMIN role.",
                    status_code=status.HTTP_400_BAD_REQUEST
                )

        with transaction.atomic():
            UserRole.objects.filter(role=role, user__in=users).delete()

        return success_response(message="Users removed from role successfully.")
