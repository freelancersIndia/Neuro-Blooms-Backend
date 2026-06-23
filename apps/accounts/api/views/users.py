from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models.user import User
from apps.accounts.api.serializers.user import UserAdminSerializer
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip

class UserAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = UserAdminSerializer
    queryset = User.objects.all().order_by('-created_at')
    lookup_field = 'id'

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

        return Response({'detail': 'User account deleted successfully.'}, status=status.HTTP_200_OK)
