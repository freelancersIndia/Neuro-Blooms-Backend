from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrDoctorOwnerOrReceptionistReadOnly
from apps.consultations.api.serializers.doctor_leave import DoctorLeaveSerializer
from apps.consultations.services.doctor_leave_service import DoctorLeaveService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class DoctorLeaveViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrDoctorOwnerOrReceptionistReadOnly]

    def list(self, request, doctor_id):
        # View-level permission check is already handled by has_permission (comparing doctor_id)
        leaves = DoctorLeaveService.list_leaves(doctor_id)
        serializer = DoctorLeaveSerializer(leaves, many=True)
        return success_response(
            message="Doctor leaves retrieved successfully.",
            data=serializer.data
        )

    def create(self, request, doctor_id):
        serializer = DoctorLeaveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        leave = DoctorLeaveService.create_leave(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            data=serializer.validated_data
        )

        response_serializer = DoctorLeaveSerializer(leave)
        return success_response(
            message="Doctor leave created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def partial_update(self, request, doctor_id, pk=None):
        serializer = DoctorLeaveSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated = DoctorLeaveService.update_leave(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            leave_id=pk,
            data=serializer.validated_data
        )

        response_serializer = DoctorLeaveSerializer(updated)
        return success_response(
            message="Doctor leave updated successfully.",
            data=response_serializer.data
        )

    def destroy(self, request, doctor_id, pk=None):
        ip_address = get_client_ip(request)
        DoctorLeaveService.delete_leave(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            leave_id=pk
        )
        return success_response(
            message="Doctor leave deleted successfully."
        )
