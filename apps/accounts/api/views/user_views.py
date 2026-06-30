from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.utils import timezone
from django.db.models import Q

from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models.user import User, AccountLock, FailedLoginAttempt, UserRole
from apps.accounts.models.session import UserSession
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.api.serializers.user import (
    UserAdminSerializer,
    UserListSerializer,
    UserDetailSerializer,
    UserUpdateSerializer,
    UserSessionSerializer,
    UserActivityLogSerializer,
)
from apps.accounts.api.serializers.create_user_serializer import CreateUserSerializer, CreatedUserResponseSerializer
from apps.accounts.services.create_user_service import CreateUserService
from apps.accounts.services.user_service import UserService
from apps.accounts.services.session_service import SessionService
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.api.pagination import UserAdminPagination
from apps.accounts.selectors.user import get_users_queryset, get_user_statistics, get_user_by_id

class UserAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserAdminSerializer
    lookup_field = 'id'
    
    # Custom pagination configuration
    pagination_class = UserAdminPagination
    pagination_message = "Users retrieved successfully."

    def get_queryset(self):
        return User.objects.filter(is_deleted=False).prefetch_related('roles')

    def list(self, request, *args, **kwargs):
        params = request.query_params.dict()
        # Handle query_params containing list of roles
        if hasattr(request.query_params, 'getlist'):
            # Convert QueryDict to standard dict while preserving lists for role
            params = {k: request.query_params.getlist(k) if k == 'role' else v for k, v in request.query_params.items()}
        queryset = get_users_queryset(params)
        
        # Prefetch counts for permission checks to avoid N+1 queries
        active_superusers_count = User.objects.filter(is_superuser=True, is_active=True, is_deleted=False).count()
        active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
        
        context = self.get_serializer_context()
        context.update({
            'active_superusers_count': active_superusers_count,
            'active_admins_count': active_admins_count,
        })
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = UserListSerializer(page, many=True, context=context)
            return self.get_paginated_response(serializer.data)
            
        serializer = UserListSerializer(queryset, many=True, context=context)
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
        
        # Prefetch counts for permission checks to avoid N+1 queries
        active_superusers_count = User.objects.filter(is_superuser=True, is_active=True, is_deleted=False).count()
        active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
        
        context = self.get_serializer_context()
        context.update({
            'active_superusers_count': active_superusers_count,
            'active_admins_count': active_admins_count,
        })
        
        # 1. Profile Information
        profile_serializer = UserDetailSerializer(user, context=context)
        
        # 2. Assigned Roles
        assigned_roles = [
            {
                "id": str(role.id),
                "name": role.name,
                "is_system": role.is_system
            }
            for role in user.roles.all()
        ]
        
        # 3. Sessions (First page, size 10)
        sessions_qs = user.sessions.all().order_by('-last_activity')
        from django.core.paginator import Paginator
        sessions_paginator = Paginator(sessions_qs, 10)
        first_session_page = sessions_paginator.get_page(1)
        sessions_data = UserSessionSerializer(first_session_page.object_list, many=True, context={'request': request}).data
        
        # 4. Activity Logs (First page, size 10)
        activity_qs = ActivityLog.objects.filter(
            Q(user=user) | Q(target_user=user)
        ).order_by('-created_at')
        activity_paginator = Paginator(activity_qs, 10)
        first_activity_page = activity_paginator.get_page(1)
        activity_data = UserActivityLogSerializer(first_activity_page.object_list, many=True).data
        
        # 5. Security Information
        failed_attempts = FailedLoginAttempt.objects.filter(email=user.email).order_by('-attempt_time')
        failed_count = failed_attempts.count()
        last_failed = failed_attempts.first().attempt_time if failed_attempts.exists() else None
        
        latest_lock = user.locks.order_by('-locked_at').first()
        
        # Unlock history
        unlock_logs = ActivityLog.objects.filter(
            target_user=user,
            action__in=[ActivityType.USER_UNLOCKED, ActivityType.ACCOUNT_UNLOCKED]
        ).order_by('-created_at')[:5]
        unlock_history = [
            {
                "timestamp": log.created_at,
                "performed_by": log.user.email if log.user else "System",
                "ip": log.ip_address,
                "description": log.description
            }
            for log in unlock_logs
        ]
        
        # Lock history
        lock_logs = ActivityLog.objects.filter(
            target_user=user,
            action__in=[ActivityType.USER_LOCKED, ActivityType.ACCOUNT_LOCKED]
        ).order_by('-created_at')[:5]
        lock_history = [
            {
                "timestamp": log.created_at,
                "performed_by": log.user.email if log.user else "System",
                "ip": log.ip_address,
                "description": log.description
            }
            for log in lock_logs
        ]
        
        # Password changed at
        pwd_log = ActivityLog.objects.filter(
            target_user=user,
            action=ActivityType.PASSWORD_CHANGED
        ).order_by('-created_at').first()
        
        # Last OTP verification
        otp_log = ActivityLog.objects.filter(
            target_user=user,
            action=ActivityType.OTP_VERIFIED
        ).order_by('-created_at').first()
        
        security_info = {
            "failed_login_attempts": failed_count,
            "last_failed_login": last_failed,
            "account_locked_at": latest_lock.locked_at if latest_lock else None,
            "account_locked_until": latest_lock.unlock_at if (latest_lock and latest_lock.is_active) else None,
            "unlock_history": unlock_history,
            "lock_history": lock_history,
            "password_changed_at": pwd_log.created_at if pwd_log else None,
            "mfa_enabled": False,
            "last_otp_verification": otp_log.created_at if otp_log else None
        }
        
        response_data = {
            **profile_serializer.data,
            "assigned_roles": assigned_roles,
            "sessions": {
                "count": sessions_paginator.count,
                "page": 1,
                "page_size": 10,
                "total_pages": sessions_paginator.num_pages,
                "results": sessions_data
            },
            "activity_logs": {
                "count": activity_paginator.count,
                "page": 1,
                "page_size": 10,
                "total_pages": activity_paginator.num_pages,
                "results": activity_data
            },
            "security_info": security_info
        }
        
        return success_response(
            message="User details retrieved successfully.",
            data=response_data
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
        
        # Track who created the user
        user.created_by = request.user
        user.save()
        
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
        
        # Prefetch counts for permission checks
        active_superusers_count = User.objects.filter(is_superuser=True, is_active=True, is_deleted=False).count()
        active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
        context = self.get_serializer_context()
        context.update({
            'active_superusers_count': active_superusers_count,
            'active_admins_count': active_admins_count,
        })
        
        response_serializer = UserDetailSerializer(user_opt, context=context)
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
    def block(self, request, id=None):
        """
        API endpoint for admin to block a user account.
        """
        user = UserService.get_user_details(id)
        try:
            UserService.block_user(
                user=user,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="User account blocked successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='lock', permission_classes=[IsAuthenticated, IsAdmin])
    def lock(self, request, id=None):
        """
        API endpoint for admin to lock a user account. (Backwards compatibility)
        """
        return self.block(request, id)

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

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def activate(self, request, id=None):
        """
        API endpoint for admin to activate a user account.
        """
        user = UserService.get_user_details(id)
        try:
            UserService.activate_user(
                user=user,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="User account activated successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsAdmin])
    def deactivate(self, request, id=None):
        """
        API endpoint for admin to deactivate a user account.
        """
        user = UserService.get_user_details(id)
        try:
            UserService.deactivate_user(
                user=user,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="User account deactivated successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='reset-password', permission_classes=[IsAuthenticated, IsAdmin])
    def reset_password(self, request, id=None):
        """
        API endpoint for admin to reset a user's password.
        """
        user = UserService.get_user_details(id)
        password = request.data.get('password')
        if not password:
            return error_response(
                message="Password is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        from django.contrib.auth.password_validation import validate_password as django_validate_password
        try:
            django_validate_password(password, user)
        except Exception as e:
            msg = e.messages[0] if hasattr(e, 'messages') else str(e)
            return error_response(
                message=msg,
                status_code=status.HTTP_400_BAD_REQUEST
            )
            
        try:
            UserService.reset_password_by_admin(
                user=user,
                new_password=password,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="Password reset successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='roles/assign', permission_classes=[IsAuthenticated, IsAdmin])
    def roles_assign(self, request, id=None):
        """
        API endpoint for admin to assign roles to a user.
        """
        user = UserService.get_user_details(id)
        role_names = request.data.get('roles')
        if role_names is None:
            return error_response(
                message="roles list is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            UserService.assign_roles(
                user=user,
                role_names=role_names,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="Roles assigned successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'], url_path='roles/remove', permission_classes=[IsAuthenticated, IsAdmin])
    def roles_remove(self, request, id=None):
        """
        API endpoint for admin to remove roles from a user.
        """
        user = UserService.get_user_details(id)
        role_names = request.data.get('roles')
        if role_names is None:
            return error_response(
                message="roles list is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )
        try:
            UserService.remove_roles(
                user=user,
                role_names=role_names,
                admin_user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="Roles removed successfully.",
                data=None
            )
        except ValidationError as e:
            return error_response(
                message=e.detail[0] if isinstance(e.detail, list) else str(e.detail),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'], url_path='sessions', permission_classes=[IsAuthenticated, IsAdmin])
    def sessions(self, request, id=None):
        """
        API endpoint for admin to list active sessions of a user.
        """
        user = UserService.get_user_details(id)
        sessions_qs = user.sessions.all().order_by('-last_activity')
        
        page = self.paginate_queryset(sessions_qs)
        if page is not None:
            serializer = UserSessionSerializer(page, many=True, context={'request': request})
            return self.get_paginated_response(serializer.data)
            
        serializer = UserSessionSerializer(sessions_qs, many=True, context={'request': request})
        return success_response(
            message="Sessions retrieved successfully.",
            data=serializer.data
        )

    def session_revoke(self, request, id=None, session_id=None):
        """
        API endpoint for admin to revoke a specific session.
        Matched by custom route in urls.py.
        """
        user = UserService.get_user_details(id)
        try:
            session = user.sessions.get(id=session_id)
        except UserSession.DoesNotExist:
            return error_response(
                message="Session not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        session.is_active = False
        session.save()
        
        ActivityLog.objects.create(
            user=request.user,
            target_user=user,
            action=ActivityType.SESSION_REVOKED,
            description=f"Admin {request.user.email} revoked session {session_id} for user {user.email}.",
            ip_address=get_client_ip(request)
        )
        
        return success_response(
            message="Session revoked successfully.",
            data=None
        )

    @action(detail=True, methods=['post'], url_path='logout-all', permission_classes=[IsAuthenticated, IsAdmin])
    def logout_all(self, request, id=None):
        """
        API endpoint for admin to logout a user from all devices.
        """
        user = UserService.get_user_details(id)
        SessionService.deactivate_all_sessions(user)
        
        ActivityLog.objects.create(
            user=request.user,
            target_user=user,
            action=ActivityType.SESSION_REVOKED,
            description=f"Admin {request.user.email} logged out all sessions for user {user.email}.",
            ip_address=get_client_ip(request)
        )
        
        return success_response(
            message="All sessions revoked successfully.",
            data=None
        )

    @action(detail=True, methods=['get'], url_path='activity', permission_classes=[IsAuthenticated, IsAdmin])
    def activity(self, request, id=None):
        """
        API endpoint for admin to get user's activity log.
        """
        user = UserService.get_user_details(id)
        activity_qs = ActivityLog.objects.filter(
            Q(user=user) | Q(target_user=user)
        ).order_by('-created_at')
        
        # Apply filters
        date_from = request.query_params.get('date_from')
        if date_from:
            activity_qs = activity_qs.filter(created_at__gte=date_from)
        date_to = request.query_params.get('date_to')
        if date_to:
            activity_qs = activity_qs.filter(created_at__lte=date_to)
        search = request.query_params.get('search')
        if search:
            activity_qs = activity_qs.filter(description__icontains=search.strip())
            
        page = self.paginate_queryset(activity_qs)
        if page is not None:
            serializer = UserActivityLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = UserActivityLogSerializer(activity_qs, many=True)
        return success_response(
            message="Activity logs retrieved successfully.",
            data=serializer.data
        )

    @action(detail=True, methods=['get'], url_path='security', permission_classes=[IsAuthenticated, IsAdmin])
    def security(self, request, id=None):
        """
        API endpoint for admin to get user's security log.
        """
        user = UserService.get_user_details(id)
        security_actions = [
            ActivityType.LOGIN,
            ActivityType.LOGOUT,
            ActivityType.FAILED_LOGIN,
            ActivityType.PASSWORD_RESET,
            ActivityType.PASSWORD_CHANGED,
            ActivityType.OTP_VERIFIED,
            ActivityType.USER_LOCKED,
            ActivityType.USER_UNLOCKED,
            ActivityType.ACCOUNT_LOCKED,
            ActivityType.SESSION_REVOKED,
            ActivityType.ACCOUNT_UNLOCKED,
            ActivityType.EMAIL_VERIFICATION_SENT,
            ActivityType.EMAIL_VERIFIED
        ]
        
        security_qs = ActivityLog.objects.filter(
            Q(user=user) | Q(target_user=user),
            action__in=security_actions
        ).order_by('-created_at')
        
        page = self.paginate_queryset(security_qs)
        if page is not None:
            serializer = UserActivityLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = UserActivityLogSerializer(security_qs, many=True)
        return success_response(
            message="Security logs retrieved successfully.",
            data=serializer.data
        )
