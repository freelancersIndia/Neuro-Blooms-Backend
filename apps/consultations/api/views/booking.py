import datetime
import traceback
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Prefetch

from apps.accounts.models.user import User
from apps.consultations.models.doctor_availability import DoctorAvailability
from apps.consultations.services.booking_service import BookingService
from apps.consultations.api.serializers.booking import (
    PublicDoctorListSerializer,
    AppointmentRequestPublicCreateSerializer
)
from apps.accounts.utils.responses import success_response, error_response

class PublicDoctorListView(APIView):
    """
    GET /api/v1/doctors/
    Returns all active doctors for dropdown selection.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            doctors = User.objects.filter(
                user_roles__role__name='DOCTOR', 
                is_active=True
            ).prefetch_related(
                Prefetch(
                    'availabilities',
                    queryset=DoctorAvailability.objects.filter(is_active=True),
                    to_attr='active_availability'
                )
            ).distinct().order_by('first_name', 'last_name')
            
            # Check if authenticated (for admin dashboard/existing tests compatibility)
            if request.user and request.user.is_authenticated:
                from apps.accounts.api.serializers.doctor import DoctorListSerializer
                serializer = DoctorListSerializer(doctors, many=True, context={'request': request})
            else:
                serializer = PublicDoctorListSerializer(doctors, many=True, context={'request': request})
            
            return success_response(
                message="Doctors retrieved successfully.",
                data=serializer.data
            )
        except Exception:
            return error_response(
                message="An unexpected error occurred while retrieving doctors.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvailableDatesView(APIView):
    """
    GET /api/v1/doctors/{doctor_id}/available-dates/
    Returns all available booking dates for the doctor.
    """
    permission_classes = [AllowAny]

    def get(self, request, doctor_id):
        try:
            dates = BookingService.get_available_dates(doctor_id)
            return success_response(
                message="Available dates retrieved successfully.",
                data=dates
            )
        except ObjectDoesNotExist as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except ValueError as e:
            # Missing clinic settings
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception:
            return error_response(
                message="An unexpected error occurred while retrieving available dates.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AvailableSlotsView(APIView):
    """
    GET /api/v1/doctors/{doctor_id}/available-slots/?date=YYYY-MM-DD
    Returns all available slots for the selected date.
    """
    permission_classes = [AllowAny]

    def get(self, request, doctor_id):
        date_str = request.query_params.get("date")
        if not date_str:
            return error_response(
                message="Date parameter is required.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            date_val = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            return error_response(
                message="Invalid date format. Use YYYY-MM-DD.",
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            slots, message = BookingService.get_available_slots(doctor_id, date_val)
            return success_response(
                message=message,
                data=slots
            )
        except ObjectDoesNotExist as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ValidationError as e:
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception:
            return error_response(
                message="An unexpected error occurred while retrieving available slots.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestCreateView(APIView):
    """
    POST /api/v1/appointment-requests/
    Creates a new AppointmentRequest.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AppointmentRequestPublicCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            instance = serializer.save()
            return success_response(
                message="Appointment request submitted successfully.",
                data={
                    "id": instance.id,
                    "request_number": instance.request_number,
                    "status": instance.status,
                    "child_first_name": instance.child_first_name,
                    "child_last_name": instance.child_last_name,
                    "preferred_date": instance.preferred_date.strftime('%Y-%m-%d'),
                    "preferred_time_slot": instance.preferred_time_slot,
                },
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return error_response(
                message="Validation failed.",
                errors=e.message_dict if hasattr(e, 'message_dict') else e.messages,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            traceback.print_exc()
            return error_response(
                message="An unexpected error occurred while submitting the request.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
