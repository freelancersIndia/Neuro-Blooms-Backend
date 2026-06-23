from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.models.session import UserSession
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.api.serializers.auth import UserSessionSerializer
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip

class UserSessionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = UserSessionSerializer
    queryset = UserSession.objects.all()
    lookup_field = 'id'

    def get_queryset(self):
        return UserSession.objects.filter(user=self.request.user, is_active=True)

    def destroy(self, request, *args, **kwargs):
        session = self.get_object()
        session.is_active = False
        session.save()

        # Log security revocation event
        ip_address = get_client_ip(request)
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.SESSION_REVOKED,
            description=f"Device session (ID: {session.id}) was revoked/deactivated.",
            ip_address=ip_address
        )

        return Response({'detail': 'Session revoked successfully.'}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='logout-all')
    def logout_all(self, request):
        ip_address = get_client_ip(request)
        active_sessions = UserSession.objects.filter(user=request.user, is_active=True)
        count = active_sessions.count()

        # Deactivate all active sessions for user
        active_sessions.update(is_active=False)

        # Log revocation event
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.SESSION_REVOKED,
            description=f"All active device sessions ({count}) were revoked.",
            ip_address=ip_address
        )

        return Response({'detail': 'Successfully logged out of all active sessions.'}, status=status.HTTP_200_OK)
