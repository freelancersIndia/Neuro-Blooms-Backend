from rest_framework import generics, serializers, status
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions.is_admin import IsAdmin
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.api.pagination import StandardPageNumberPagination

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
    pagination_class = StandardPageNumberPagination
    pagination_message = "Security logs retrieved successfully."

    def get_queryset(self):
        queryset = ActivityLog.objects.all().order_by('-created_at')
        
        # Filter by action (?action=...)
        action_query = self.request.query_params.get('action')
        if action_query:
            queryset = queryset.filter(action=action_query.strip())
            
        # Filter by user_id (?user_id=...)
        user_id_query = self.request.query_params.get('user_id')
        if user_id_query:
            queryset = queryset.filter(user_id=user_id_query.strip())
            
        # Filter by date_from (?date_from=...)
        date_from_query = self.request.query_params.get('date_from')
        if date_from_query:
            queryset = queryset.filter(created_at__gte=date_from_query.strip())
            
        # Filter by date_to (?date_to=...)
        date_to_query = self.request.query_params.get('date_to')
        if date_to_query:
            queryset = queryset.filter(created_at__lte=date_to_query.strip())
            
        return queryset
