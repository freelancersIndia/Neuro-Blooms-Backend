from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework import status
import datetime
import uuid

from apps.accounts.models.user import User
from apps.accounts.api.serializers.doctor import DoctorListSerializer
from apps.consultations.api.serializers.appointment_request import AppointmentRequestCreateSerializer
from apps.consultations.services.appointment_service import AppointmentService
from apps.accounts.services.email_service import EmailService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class PublicDoctorListView(APIView):
    """
    GET /api/v1/public/doctors/
    Returns a list of all active doctors for public booking selection.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        doctors = User.objects.filter(
            user_roles__role__name='DOCTOR', 
            is_active=True
        ).distinct().order_by('first_name', 'last_name')
        serializer = DoctorListSerializer(doctors, many=True, context={'request': request})
        return success_response(
            message="Active doctors retrieved successfully.",
            data=serializer.data
        )

class PublicAvailableSlotsView(APIView):
    """
    GET /api/v1/public/appointments/available-slots/
    Returns available appointment slots for a doctor on a specific date.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        doctor_id = request.query_params.get("doctor_id")
        appointment_date_str = request.query_params.get("appointment_date")

        if not doctor_id or not appointment_date_str:
            return success_response(
                message="doctor_id and appointment_date are required.",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )

        try:
            appointment_date = datetime.datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
        except ValueError:
            return success_response(
                message="Invalid date format. Use YYYY-MM-DD.",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )

        result = AppointmentService.generate_available_slots(doctor_id, appointment_date)
        message = result.get("message", "Available slots retrieved successfully.")

        return success_response(
            message=message,
            data=result
        )

class PublicAppointmentRequestCreateView(APIView):
    """
    POST /api/v1/public/appointment-requests/
    Submits a new appointment request and sends a confirmation email.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = AppointmentRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Generate unique request number: REQ-YYYYMMDD-XXXX
        today_str = datetime.date.today().strftime("%Y%m%d")
        unique_suffix = uuid.uuid4().hex[:4].upper()
        request_number = f"REQ-{today_str}-{unique_suffix}"

        # Save model instance
        appointment_request = serializer.save(
            request_number=request_number,
            status="PENDING"
        )

        # Send confirmation email
        parent_name = f"{appointment_request.parent_first_name} {appointment_request.parent_last_name}"
        EmailService.send_appointment_request_confirmation(
            email=appointment_request.email,
            parent_name=parent_name,
            request_number=appointment_request.request_number
        )

        return success_response(
            message="Appointment request submitted successfully.",
            data={
                "id": appointment_request.id,
                "request_number": appointment_request.request_number,
                "status": appointment_request.status,
                "child_first_name": appointment_request.child_first_name,
                "child_last_name": appointment_request.child_last_name,
                "preferred_date": appointment_request.preferred_date,
                "preferred_time_slot": appointment_request.preferred_time_slot,
            },
            status_code=status.HTTP_201_CREATED
        )
