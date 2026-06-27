from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrReceptionistReadOnly
from apps.consultations.api.serializers.clinic_holiday import ClinicHolidaySerializer
from apps.consultations.services.clinic_holiday_service import ClinicHolidayService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class ClinicHolidayViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistReadOnly]

    def list(self, request):
        holidays = ClinicHolidayService.list_holidays()
        serializer = ClinicHolidaySerializer(holidays, many=True)
        return success_response(
            message="Holidays retrieved successfully.",
            data=serializer.data
        )

    def create(self, request):
        serializer = ClinicHolidaySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        holiday = ClinicHolidayService.create_holiday(
            user=request.user,
            ip_address=ip_address,
            data=serializer.validated_data
        )

        response_serializer = ClinicHolidaySerializer(holiday)
        return success_response(
            message="Clinic holiday created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk=None):
        serializer = ClinicHolidaySerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated_holiday = ClinicHolidayService.update_holiday(
            user=request.user,
            ip_address=ip_address,
            holiday_id=pk,
            data=serializer.validated_data
        )

        response_serializer = ClinicHolidaySerializer(updated_holiday)
        return success_response(
            message="Clinic holiday updated successfully.",
            data=response_serializer.data
        )

    def destroy(self, request, pk=None):
        ip_address = get_client_ip(request)
        ClinicHolidayService.delete_holiday(
            user=request.user,
            ip_address=ip_address,
            holiday_id=pk
        )
        return success_response(
            message="Clinic holiday deleted successfully."
        )
