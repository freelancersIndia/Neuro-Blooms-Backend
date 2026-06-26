import logging
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle

from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.consultations.api.serializers import PublicConsultationRequestSerializer
from apps.consultations.services import AppointmentRequestService, DuplicateRequestException

logger = logging.getLogger(__name__)

class PublicConsultationRequestAPIView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request, *args, **kwargs):
        """
        Creates a new public appointment/consultation request.
        No authentication required. Includes IP throttling for anonymous users.
        """
        serializer = PublicConsultationRequestSerializer(data=request.data)
        
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as e:
            # Log validation failures without logging plain text PII
            logger.warning(f"Public consultation request validation failed. Errors: {getattr(e, 'detail', str(e))}")
            raise e

        ip_address = get_client_ip(request)

        try:
            appointment_request = AppointmentRequestService.create_public_request(
                validated_data=serializer.validated_data,
                ip_address=ip_address
            )
            
            # Format and return standardized success response (201 Created)
            return success_response(
                message="Consultation request submitted successfully.",
                data={
                    "request_number": appointment_request.request_number,
                    "status": appointment_request.status,
                    "preferred_date": str(appointment_request.preferred_date),
                    "preferred_time_slot": appointment_request.preferred_time_slot,
                },
                status_code=status.HTTP_201_CREATED
            )

        except DuplicateRequestException as e:
            # Log duplicate detection without PII (already logged in service, but we also log generic message here)
            logger.warning(f"Duplicate consultation request conflict: {str(e)}")
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_409_CONFLICT)

        except Exception as e:
            logger.error(f"Unexpected exception during public consultation request creation: {str(e)}", exc_info=True)
            return error_response(
                message="An unexpected error occurred while processing your request.",
                errors=None,
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
