from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models.activity_log import ActivityLog

class ActivityLogSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source='user.email', read_only=True, default="Anonymous")

    class Meta:
        model = ActivityLog
        fields = ['id', 'user_email', 'action', 'description', 'ip_address', 'created_at']

class SecurityLogListView(generics.ListAPIView):
    """
    Endpoint for administrators to view security and activity logs.
    """
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = ActivityLogSerializer
    queryset = ActivityLog.objects.all().order_by('-created_at')
