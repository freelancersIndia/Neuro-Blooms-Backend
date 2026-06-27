from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser
from apps.consultations.api.permissions import IsAdminOrReceptionistReadOnly
from apps.consultations.api.serializers.clinic_settings import ClinicSettingsSerializer, ClinicSettingsUpdateSerializer
from apps.consultations.services.clinic_settings_service import ClinicSettingsService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class ClinicSettingsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistReadOnly]
    parser_classes = [MultiPartParser, FormParser]

    def get(self, request):
        settings = ClinicSettingsService.get_settings()
        serializer = ClinicSettingsSerializer(settings, context={'request': request})
        return success_response(
            message="Clinic settings retrieved successfully.",
            data=serializer.data
        )

    def patch(self, request):
        settings = ClinicSettingsService.get_settings()
        serializer = ClinicSettingsUpdateSerializer(settings, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        updated_settings = ClinicSettingsService.update_settings(
            user=request.user,
            ip_address=ip_address,
            data=serializer.validated_data
        )

        response_serializer = ClinicSettingsSerializer(updated_settings, context={'request': request})
        return success_response(
            message="Clinic settings updated successfully.",
            data=response_serializer.data
        )
