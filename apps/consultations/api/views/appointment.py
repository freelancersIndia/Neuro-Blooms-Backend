from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from apps.consultations.api.serializers.appointment import (
    AvailableSlotsQuerySerializer,
    SlotValidationSerializer,
    AppointmentBookingSerializer,
    AppointmentDetailSerializer
)
from apps.consultations.services.appointment_service import AppointmentService
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.utils.ip import get_client_ip

class AvailableSlotsAPIView(APIView):
    """
    get:
    Summary: Generate Available Slots
    Description:
      Dynamically generates all available appointment slots for a doctor on a given date.
      No static slot records are stored in the database; availability is calculated at runtime by
      evaluating clinic settings, weekly schedules, holidays, breaks, doctor availability preferences,
      working hours, leaves, blocked slots, and existing confirmed appointments.
    
    Permissions:
      - IsAuthenticated (Admin, Receptionist, Doctor)
      
    Query Parameters:
      - doctor_id (UUID, Required): Unique identifier of the doctor.
      - appointment_date (Date, Required): Date for which slots are requested (YYYY-MM-DD).
      - appointment_type (String, Optional): Choice of INITIAL, FOLLOW_UP, REVIEW, etc.
      
    Validation Rules:
      - Doctor must exist and have the Doctor role.
      - Appointment date is required, cannot be in the past, and must fall within the clinic's booking window.
      - Same-day booking must be allowed in clinic settings if the date is today.
      
    Business Rules:
      - Clinic settings (slot duration, booking window, same-day booking) are loaded.
      - Weekly schedule and holidays are checked.
      - Doctor's availability preference and working day override are evaluated.
      - Doctor leaves and blocked times are removed.
      - Existing confirmed, checked-in, in-consultation, and completed appointments are excluded.
      - Maximum daily patient limit for the doctor is respected.
      - Slots starting in the past on the current day are filtered out.
      
    Example Request:
      GET /api/v1/appointments/available-slots/?doctor_id=d3b07384-d113-4956-a5d8-472d7d56637e&appointment_date=2026-07-20
      
    Example Response (Success):
      {
        "success": true,
        "message": "Available slots retrieved successfully.",
        "data": {
          "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "date": "2026-07-20",
          "available_slots": [
            {"start": "09:00", "end": "09:30"},
            {"start": "09:30", "end": "10:00"}
          ]
        }
      }
      
    Example Response (Clinic Closed / Holiday / Leave / Limit Reached):
      {
        "success": true,
        "message": "Clinic Closed",
        "data": {
          "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "date": "2026-07-20",
          "available_slots": [],
          "message": "Clinic Closed"
        }
      }
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = AvailableSlotsQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        doctor_id = serializer.validated_data["doctor_id"]
        appointment_date = serializer.validated_data["appointment_date"]

        result = AppointmentService.generate_available_slots(doctor_id, appointment_date)
        message = result.get("message", "Available slots retrieved successfully.")

        return success_response(
            message=message,
            data=result
        )


class ValidateSlotAPIView(APIView):
    """
    post:
    Summary: Validate Selected Slot
    Description:
      Validates a selected slot immediately before appointment creation.
      This acts as a real-time check to prevent race conditions where multiple users try to book the same slot.
      
    Permissions:
      - IsAuthenticated (Admin, Receptionist, Doctor)
      
    Request Schema (JSON):
      - doctor_id (UUID, Required): Unique identifier of the doctor.
      - appointment_date (Date, Required): Date of the appointment (YYYY-MM-DD).
      - start_time (Time, Required): Start time of the slot (HH:MM).
      
    Validation Rules:
      - Same as available slots generation.
      
    Business Rules:
      - Runs the entire scheduling engine dynamically to confirm the slot is still free.
      - Never trusts cached availability.
      
    Example Request:
      POST /api/v1/appointments/validate-slot/
      {
        "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
        "appointment_date": "2026-07-20",
        "start_time": "10:30"
      }
      
    Example Response (Valid):
      {
        "success": true,
        "message": "Slot validation completed.",
        "data": {
          "valid": true
        }
      }
      
    Example Response (Invalid):
      {
        "success": true,
        "message": "Slot validation completed.",
        "data": {
          "valid": false,
          "reason": "Slot already booked."
        }
      }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SlotValidationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        doctor_id = serializer.validated_data["doctor_id"]
        appointment_date = serializer.validated_data["appointment_date"]
        start_time = serializer.validated_data["start_time"]

        result = AppointmentService.validate_slot(doctor_id, appointment_date, start_time)
        return success_response(
            message="Slot validation completed.",
            data=result
        )


class AppointmentBookingAPIView(APIView):
    """
    post:
    Summary: Book Appointment
    Description:
      Creates a confirmed appointment using an available slot.
      The booking operation runs in an atomic database transaction and acquires a write-lock on the
      doctor's appointments for that day to prevent concurrent bookings (race conditions).
      
    Permissions:
      - IsAuthenticated (Admin, Receptionist)
      
    Request Schema (JSON):
      - patient_id (UUID, Required): Unique identifier of the patient.
      - doctor_id (UUID, Required): Unique identifier of the doctor.
      - appointment_date (Date, Required): Date of the appointment (YYYY-MM-DD).
      - start_time (Time, Required): Start time of the slot (HH:MM).
      - appointment_type (String, Required): Choice of INITIAL, FOLLOW_UP, REVIEW, etc.
      - notes (String, Optional): Notes or reason for visit.
      
    Validation Rules:
      - Patient and Doctor must exist.
      - Doctor must have the Doctor role.
      - Appointment date and slot must be valid.
      - Doctor must not be already booked for the same slot.
      - Patient must not be already booked for the same slot.
      
    Business Rules:
      - Acquires database lock on the doctor/date combination.
      - Rechecks availability immediately before creating the record.
      - Automatically starts in CONFIRMED status.
      - Automatically creates an AppointmentTimeline entry ("Appointment Confirmed").
      - Creates an ActivityLog entry for auditing.
      
    Example Request:
      POST /api/v1/appointments/
      {
        "patient_id": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
        "doctor_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
        "appointment_date": "2026-07-20",
        "start_time": "10:30",
        "appointment_type": "INITIAL",
        "notes": "Speech delay consultation"
      }
      
    Example Response (Success):
      {
        "success": true,
        "message": "Appointment created successfully.",
        "data": {
          "id": "1a2b3c4d-5e6f-7a8b-9c0d-1e2f3a4b5c6d",
          "appointment_number": "APT-20260720-A3B9C2",
          "patient": "9a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
          "patient_name": "Jimmy Doe",
          "doctor": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "doctor_name": "Dr. John Smith",
          "appointment_type": "INITIAL",
          "appointment_type_display": "Initial",
          "booking_source": "RECEPTIONIST",
          "booking_source_display": "Receptionist",
          "status": "CONFIRMED",
          "status_display": "Confirmed",
          "appointment_date": "2026-07-20",
          "start_time": "10:30:00",
          "end_time": "11:00:00",
          "duration_minutes": 30,
          "visit_reason": "Speech delay consultation"
        }
      }
      
    Example Response (Conflict / Slot Taken):
      {
        "success": false,
        "message": "Validation failed.",
        "errors": {
          "non_field_errors": ["Selected slot is no longer available. Reason: Slot already booked."]
        }
      }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AppointmentBookingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        appointment = AppointmentService.create_appointment(
            user=request.user,
            ip_address=ip_address,
            patient_id=serializer.validated_data["patient_id"],
            doctor_id=serializer.validated_data["doctor_id"],
            appointment_date=serializer.validated_data["appointment_date"],
            start_time=serializer.validated_data["start_time"],
            appointment_type=serializer.validated_data["appointment_type"],
            notes=serializer.validated_data.get("notes", "")
        )

        response_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment created successfully.",
            data=response_serializer.data,
            status_code=status.HTTP_201_CREATED
        )
