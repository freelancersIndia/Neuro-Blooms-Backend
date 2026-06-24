from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models.session import UserSession
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.api.serializers.auth import UserSessionSerializer
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response

class UserSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer
    queryset = UserSession.objects.all()
    lookup_field = 'id'

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return success_response(
            message="Active sessions retrieved successfully.",
            data=serializer.data
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return success_response(
            message="Session retrieved successfully.",
            data=serializer.data
        )

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        session.is_active = False
        session.save()

        # Blacklist the refresh token associated with this session
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            outstanding = OutstandingToken.objects.filter(jti=session.refresh_token_jti).first()
            if outstanding:
                BlacklistedToken.objects.get_or_create(token=outstanding)
        except Exception:
            pass

        # Log security revocation event
        ip_address = get_client_ip(request)
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.SESSION_REVOKED,
            description=f"Device session (ID: {session.id}) was revoked/deactivated and blacklisted.",
            ip_address=ip_address
        )

        return success_response(message='Session revoked successfully.', data=None)

    @action(detail=False, methods=['post'], url_path='logout-all')
    def logout_all(self, request):
        ip_address = get_client_ip(request)
        active_sessions = list(UserSession.objects.filter(user=request.user, is_active=True))
        count = len(active_sessions)

        # Blacklist and deactivate each active session
        for session in active_sessions:
            try:
                from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
                outstanding = OutstandingToken.objects.filter(jti=session.refresh_token_jti).first()
                if outstanding:
                    BlacklistedToken.objects.get_or_create(token=outstanding)
            except Exception:
                pass
            session.is_active = False
            session.save()

        # Log revocation event
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.SESSION_REVOKED,
            description=f"All active device sessions ({count}) were revoked and blacklisted.",
            ip_address=ip_address
        )

        return success_response(message='Successfully logged out of all active sessions.', data=None)
