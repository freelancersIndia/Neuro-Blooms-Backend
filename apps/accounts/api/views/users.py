from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db.models import Q

from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models.user import User, AccountLock, FailedLoginAttempt
from apps.accounts.api.serializers.user import UserAdminSerializer
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.api.pagination import StandardPageNumberPagination

class UserAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserAdminSerializer
    lookup_field = 'id'
    
    # Custom pagination configuration
    pagination_class = StandardPageNumberPagination
    pagination_message = "Users retrieved successfully."

    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        
        # 1. Search filter (?search=...)
        search_query = self.request.query_params.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(phone_number__icontains=search_query)
            )
            
        # 2. Role filter (?role=...)
        role_query = self.request.query_params.get('role')
        if role_query:
            queryset = queryset.filter(roles__name__iexact=role_query.strip())
            
        # 3. Status filter (?is_active=...)
        is_active_query = self.request.query_params.get('is_active')
        if is_active_query:
            is_active_bool = is_active_query.lower() in ('true', '1', 't')
            queryset = queryset.filter(is_active=is_active_bool)
            
        return queryset

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            message="User retrieved successfully.",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return success_response(
            message="User created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return success_response(
            message="User updated successfully.",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        user = self.get_object()
        email = user.email
        user.delete()

        # Log Administrative user deletion event
        ip_address = get_client_ip(request)
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.USER_DISABLED,
            description=f"User {email} was permanently deleted from the system.",
            ip_address=ip_address
        )

        return success_response(
            message='User account deleted successfully.',
            data=None
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def unlock(self, request, id=None):
        """
        API endpoint for admin to unlock a user account.
        """
        target_user = self.get_object()
        now = timezone.now()

        # Find active account lock
        active_lock = AccountLock.objects.filter(
            user=target_user,
            is_active=True,
            unlock_at__gt=now
        ).first()

        if not active_lock:
            return error_response(
                message="User is not locked.",
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        # Deactivate the lock
        active_lock.is_active = False
        active_lock.save()

        # Clear failed login attempts
        FailedLoginAttempt.objects.filter(email=target_user.email).delete()

        # Create Activity Log
        ip_address = get_client_ip(request)
        ActivityLog.objects.create(
            user=target_user,
            action=ActivityType.ACCOUNT_UNLOCKED,
            description=f"Account unlocked by administrator {request.user.email}.",
            ip_address=ip_address
        )

        return success_response(
            message="User account unlocked successfully.",
            data=None
        )
