from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrDoctorOwnerOrReceptionistReadOnly
from apps.consultations.api.serializers.doctor_working_day import DoctorWorkingDaySerializer, DoctorWorkingDayBulkUpdateSerializer
from apps.consultations.services.doctor_working_day_service import DoctorWorkingDayService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class DoctorWorkingDayAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrDoctorOwnerOrReceptionistReadOnly]

    def get(self, request, doctor_id):
        # Trigger retrieve (auto-creates if missing)
        working_days = DoctorWorkingDayService.get_working_days(doctor_id)
        if working_days:
            # Check permissions on the first element (which represents ownership of the schedule)
            self.check_object_permissions(request, working_days[0])

        serializer = DoctorWorkingDaySerializer(working_days, many=True)
        return success_response(
            message="Doctor working days retrieved successfully.",
            data=serializer.data
        )

    def patch(self, request, doctor_id):
        working_days = DoctorWorkingDayService.get_working_days(doctor_id)
        if working_days:
            self.check_object_permissions(request, working_days[0])

        serializer = DoctorWorkingDayBulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated = DoctorWorkingDayService.bulk_update(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            data_list=serializer.validated_data["working_days"]
        )

        response_serializer = DoctorWorkingDaySerializer(updated, many=True)
        return success_response(
            message="Doctor working days updated successfully.",
            data=response_serializer.data
        )
