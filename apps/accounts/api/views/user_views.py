from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models.user import User, AccountLock, FailedLoginAttempt
from apps.accounts.api.serializers.user import UserAdminSerializer, UserListSerializer, UserDetailSerializer, UserUpdateSerializer
from apps.accounts.api.serializers.create_user_serializer import CreateUserSerializer, CreatedUserResponseSerializer
from apps.accounts.services.create_user_service import CreateUserService
from apps.accounts.services.user_service import UserService
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.api.pagination import StandardPageNumberPagination, UserAdminPagination
from apps.accounts.selectors.user import get_users_queryset, get_user_statistics, get_user_by_id

class UserAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserAdminSerializer
    lookup_field = 'id'
    
    # Custom pagination configuration
    pagination_class = UserAdminPagination
    pagination_message = "Users retrieved successfully."

    def get_queryset(self):
        return User.objects.all().prefetch_related('roles')

    def list(self, request, *args, **kwargs):
        params = request.query_params.dict()
        queryset = get_users_queryset(params)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserListSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            
        serializer = UserListSerializer(queryset, many=True, context={'request': request})
        return success_response(
            message=self.pagination_message,
            data=serializer.data
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsAdmin])
    def statistics(self, request):
        """
        API endpoint for admin to get users statistics.
        """
        stats = get_user_statistics()
        return success_response(
            message="User statistics retrieved successfully.",
            data=stats
        )

    def retrieve(self, request, *args, **kwargs):
        user_id = self.kwargs.get('id')
        user = UserService.get_user_details(user_id)
        serializer = UserDetailSerializer(user, context={'request': request})
        return success_response(
            message="User details retrieved successfully.",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        serializer = CreateUserSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        validated_data = serializer.validated_data
        ip_address = get_client_ip(request)
        
        user = CreateUserService.create_user(
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name'],
            email=validated_data['email'],
            password=validated_data['password'],
            roles=validated_data['roles'],
            phone_number=validated_data.get('phone_number'),
            profile_image=validated_data.get('profile_image'),
            is_active=validated_data.get('is_active', True),
            is_verified=validated_data.get('is_verified', False),
            admin_user=request.user,
            ip_address=ip_address
        )
        
        # Optimize database query for roles retrieval
        user = User.objects.prefetch_related('roles').get(id=user.id)
        
        response_serializer = CreatedUserResponseSerializer(user, context={'request': request})
        return success_response(
            message="User created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        user_id = self.kwargs.get('id')
        instance = UserService.get_user_details(user_id)
        
        serializer = UserUpdateSerializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        user = UserService.update_user(
            user_id=instance.id,
            admin_user=request.user,
            ip_address=get_client_ip(request),
            **serializer.validated_data
        )
        
        # Optimize for response serialization
        user_opt = UserService.get_user_details(user.id)
        response_serializer = UserDetailSerializer(user_opt, context={'request': request})
        return success_response(
            message="User updated successfully.",
            data=response_serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        user_id = self.kwargs.get('id')
        user = UserService.get_user_details(user_id)
        
        try:
            UserService.delete_user(
                user=user,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message='User deleted successfully.',
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def lock(self, request, id=None):
        """
        API endpoint for admin to lock a user account.
        """
        user = UserService.get_user_details(id)
        try:
            UserService.lock_user(
                user=user,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="User account locked successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def unlock(self, request, id=None):
        """
        API endpoint for admin to unlock a user account.
        """
        user = UserService.get_user_details(id)
        try:
            UserService.unlock_user(
                user=user,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="User account unlocked successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )
