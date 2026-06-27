from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrReceptionistReadOnly
from apps.consultations.api.serializers.weekly_schedule import WeeklyScheduleSerializer, WeeklyScheduleBulkUpdateSerializer
from apps.consultations.services.weekly_schedule_service import WeeklyScheduleService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class WeeklyScheduleAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistReadOnly]

    def get(self, request):
        schedule = WeeklyScheduleService.get_schedule()
        serializer = WeeklyScheduleSerializer(schedule, many=True)
        return success_response(
            message="Weekly schedule retrieved successfully.",
            data=serializer.data
        )

    def patch(self, request):
        serializer = WeeklyScheduleBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated_schedule = WeeklyScheduleService.bulk_update(
            user=request.user,
            ip_address=ip_address,
            data_list=serializer.validated_data["schedules"]
        )

        response_serializer = WeeklyScheduleSerializer(updated_schedule, many=True)
        return success_response(
            message="Weekly schedule updated successfully.",
            data=response_serializer.data
        )
