from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from apps.accounts.api.serializers.profile import ProfileSerializer
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.utils.ip import get_client_ip

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = ProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        # Log profile update event
        ip_address = get_client_ip(request)
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.USER_UPDATED,
            description="User updated their own profile details.",
            ip_address=ip_address
        )

        return Response(serializer.data, status=status.HTTP_200_OK)
