from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrDoctorOwnerOrReceptionistReadOnly
from apps.consultations.api.serializers.doctor_blocked_slot import DoctorBlockedSlotSerializer
from apps.consultations.services.doctor_blocked_slot_service import DoctorBlockedSlotService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class DoctorBlockedSlotViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated, IsAdminOrDoctorOwnerOrReceptionistReadOnly]

    def list(self, request, doctor_id):
        blocked_slots = DoctorBlockedSlotService.list_blocked_slots(doctor_id)
        serializer = DoctorBlockedSlotSerializer(blocked_slots, many=True)
        return success_response(
            message="Doctor blocked slots retrieved successfully.",
            data=serializer.data
        )

    def create(self, request, doctor_id):
        serializer = DoctorBlockedSlotSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        blocked_slot = DoctorBlockedSlotService.create_blocked_slot(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            data=serializer.validated_data
        )

        response_serializer = DoctorBlockedSlotSerializer(blocked_slot)
        return success_response(
            message="Doctor blocked slot created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )

    def partial_update(self, request, doctor_id, pk=None):
        serializer = DoctorBlockedSlotSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated = DoctorBlockedSlotService.update_blocked_slot(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            block_id=pk,
            data=serializer.validated_data
        )

        response_serializer = DoctorBlockedSlotSerializer(updated)
        return success_response(
            message="Doctor blocked slot updated successfully.",
            data=response_serializer.data
        )

    def destroy(self, request, doctor_id, pk=None):
        ip_address = get_client_ip(request)
        DoctorBlockedSlotService.delete_blocked_slot(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            block_id=pk
        )
        return success_response(
            message="Doctor blocked slot deleted successfully."
        )
