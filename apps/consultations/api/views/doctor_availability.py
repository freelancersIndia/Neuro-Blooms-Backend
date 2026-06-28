from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from apps.consultations.api.permissions import IsAdminOrDoctorOwnerOrReceptionistReadOnly
from apps.consultations.api.serializers.doctor_availability import DoctorAvailabilitySerializer
from apps.consultations.services.doctor_availability_service import DoctorAvailabilityService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class DoctorAvailabilityAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrDoctorOwnerOrReceptionistReadOnly]

    def get(self, request, doctor_id):
        availability = DoctorAvailabilityService.get_availability(doctor_id)
        # Note: we need to pass the object to permission check manually since it's an APIView
        self.check_object_permissions(request, availability)
        
        serializer = DoctorAvailabilitySerializer(availability)
        return success_response(
            message="Doctor availability retrieved successfully.",
            data=serializer.data
        )

    def patch(self, request, doctor_id):
        availability = DoctorAvailabilityService.get_availability(doctor_id)
        self.check_object_permissions(request, availability)

        serializer = DoctorAvailabilitySerializer(availability, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated = DoctorAvailabilityService.update_availability(
            user=request.user,
            ip_address=ip_address,
            doctor_id=doctor_id,
            # Pass validated_data representing source mappings
            data=serializer.validated_data
        )

        response_serializer = DoctorAvailabilitySerializer(updated)
        return success_response(
            message="Doctor availability updated successfully.",
            data=response_serializer.data
        )
