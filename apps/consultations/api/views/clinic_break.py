from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrReceptionistReadOnly
from apps.consultations.api.serializers.clinic_break import ClinicBreakSerializer
from apps.consultations.services.clinic_break_service import ClinicBreakService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class ClinicBreakViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistReadOnly]

    def list(self, request):
        breaks = ClinicBreakService.list_breaks()
        serializer = ClinicBreakSerializer(breaks, many=True)
        return success_response(
            message="Clinic breaks retrieved successfully.",
            data=serializer.data
        )

    def create(self, request):
        serializer = ClinicBreakSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        clinic_break = ClinicBreakService.create_break(
            user=request.user,
            ip_address=ip_address,
            data=serializer.validated_data
        )

        response_serializer = ClinicBreakSerializer(clinic_break)
        return success_response(
            message="Clinic break created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def partial_update(self, request, pk=None):
        serializer = ClinicBreakSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated_break = ClinicBreakService.update_break(
            user=request.user,
            ip_address=ip_address,
            break_id=pk,
            data=serializer.validated_data
        )

        response_serializer = ClinicBreakSerializer(updated_break)
        return success_response(
            message="Clinic break updated successfully.",
            data=response_serializer.data
        )

    def destroy(self, request, pk=None):
        ip_address = get_client_ip(request)
        ClinicBreakService.delete_break(
            user=request.user,
            ip_address=ip_address,
            break_id=pk
        )
        return success_response(
            message="Clinic break deleted successfully."
        )
