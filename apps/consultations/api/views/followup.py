from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from apps.consultations.api.permissions import IsDoctorWriteOrAdminOrReceptionistReadOnly
from apps.consultations.services.followup_service import FollowupService
from apps.consultations.api.serializers.followup import (
    FollowupDecisionSerializer,
    FollowupCreateSerializer,
    FollowupDetailSerializer,
    FollowupUpdateSerializer,
    FollowupCancelSerializer,
    TreatmentCaseDetailSerializer,
    TreatmentCaseCloseSerializer,
    TreatmentCaseReopenSerializer,
    FollowupAppointmentSerializer
)

class FollowupDecisionAPIView(APIView):
    """
    post:
    Summary: Record Follow-up Decision
    Description:
      Allows the doctor to decide if a follow-up is required or if the treatment is complete.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Only assigned Doctor can write)
      
    Business Rules:
      - Only completed consultations can have a follow-up decision recorded.
      - Cannot execute this decision twice.
      - If requires_followup is false, the treatment case is automatically closed.
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request, consultation_id):
        serializer = FollowupDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        result = FollowupService.record_followup_decision(
            user=request.user,
            ip_address=ip_address,
            consultation_id=consultation_id,
            requires_followup=serializer.validated_data["requires_followup"]
        )
        
        return Response({
            "success": True,
            "message": result["message"],
            "data": {
                "requires_followup": result["requires_followup"]
            }
        }, status=status.HTTP_200_OK)


class FollowupCreateAPIView(APIView):
    """
    post:
    Summary: Create Follow-up Appointment
    Description:
      Creates a follow-up appointment directly in CONFIRMED status.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Only assigned Doctor can write)
      
    Business Rules:
      - Follow-up appointments bypass the reception request and approval workflow.
      - They are immediately confirmed and appear on the reception dashboard.
      - Slot availability is checked against the scheduling engine.
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request):
        serializer = FollowupCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        appointment = FollowupService.create_followup(
            user=request.user,
            ip_address=ip_address,
            data=serializer.validated_data
        )
        
        response_serializer = FollowupAppointmentSerializer(appointment)
        return Response({
            "success": True,
            "message": "Follow-up appointment created successfully.",
            "data": response_serializer.data
        }, status=status.HTTP_201_CREATED)


class FollowupDetailAPIView(APIView):
    """
    get:
    Summary: Get Follow-up Appointment Details
    Description:
      Retrieves complete information about a follow-up appointment including previous clinical notes.
      
    patch:
    Summary: Update Follow-up Details
    Description:
      Updates follow-up appointment details (date, time, reason, notes).
      Re-validates slots if date/time changes.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Only assigned Doctor can write/PATCH; others Read-Only)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, appointment_id):
        details = FollowupService.get_followup_details(
            user=request.user,
            appointment_id=appointment_id
        )
        serializer = FollowupDetailSerializer(details)
        return Response({
            "success": True,
            "message": "Follow-up details retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def patch(self, request, appointment_id):
        serializer = FollowupUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        appointment = FollowupService.update_followup(
            user=request.user,
            ip_address=ip_address,
            appointment_id=appointment_id,
            data=serializer.validated_data
        )
        
        response_serializer = FollowupAppointmentSerializer(appointment)
        return Response({
            "success": True,
            "message": "Follow-up appointment updated successfully.",
            "data": response_serializer.data
        }, status=status.HTTP_200_OK)


class PatientFollowupsListAPIView(APIView):
    """
    get:
    Summary: List Patient Follow-ups
    Description:
      Retrieves a list of all follow-up appointments for a patient.
      Supports filtering by doctor, start_date, and end_date, and ordering.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, patient_id):
        filters = {
            "doctor": request.query_params.get("doctor"),
            "start_date": request.query_params.get("start_date"),
            "end_date": request.query_params.get("end_date"),
        }
        ordering = request.query_params.get("ordering")
        
        qs = FollowupService.get_patient_followups(
            patient_id=patient_id,
            filters=filters,
            ordering=ordering
        )
        
        serializer = FollowupAppointmentSerializer(qs, many=True)
        return Response({
            "success": True,
            "message": "Patient follow-ups retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class FollowupCancelAPIView(APIView):
    """
    post:
    Summary: Cancel Follow-up Appointment
    Description:
      Cancels a follow-up appointment and releases the booked slot.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Only assigned Doctor can write)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request, appointment_id):
        serializer = FollowupCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        FollowupService.cancel_followup(
            user=request.user,
            ip_address=ip_address,
            appointment_id=appointment_id,
            reason=serializer.validated_data["reason"]
        )
        
        return Response({
            "success": True,
            "message": "Follow-up appointment cancelled successfully."
        }, status=status.HTTP_200_OK)


class TreatmentCaseDetailAPIView(APIView):
    """
    get:
    Summary: Get Patient Treatment Journey
    Description:
      Retrieves the complete treatment case history for a patient.
      Includes all consultations, follow-ups, attachments, and timeline events.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, patient_id):
        journey = FollowupService.get_treatment_case(patient_id=patient_id)
        serializer = TreatmentCaseDetailSerializer(journey)
        return Response({
            "success": True,
            "message": "Treatment case journey retrieved successfully.",
            "data": serializer.data
        }, status=status.HTTP_200_OK)


class TreatmentCaseCloseAPIView(APIView):
    """
    post:
    Summary: Close Treatment Case
    Description:
      Closes the active treatment case.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Only assigned Doctor can write)
      
    Business Rules:
      - Cannot close the case if there are pending consultations or future appointments.
      - Patient remains active, but case status changes to CASE_CLOSED.
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request, patient_id):
        serializer = TreatmentCaseCloseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        FollowupService.close_treatment_case(
            user=request.user,
            ip_address=ip_address,
            patient_id=patient_id,
            closing_summary=serializer.validated_data["closing_summary"],
            outcome=serializer.validated_data["outcome"]
        )
        
        return Response({
            "success": True,
            "message": "Treatment case closed successfully."
        }, status=status.HTTP_200_OK)


class TreatmentCaseReopenAPIView(APIView):
    """
    post:
    Summary: Reopen Treatment Case
    Description:
      Reopens a previously closed treatment case.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Only assigned Doctor can write)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request, patient_id):
        serializer = TreatmentCaseReopenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
        FollowupService.reopen_treatment_case(
            user=request.user,
            ip_address=ip_address,
            patient_id=patient_id,
            reason=serializer.validated_data["reason"]
        )
        
        return Response({
            "success": True,
            "message": "Treatment case reopened successfully."
        }, status=status.HTTP_200_OK)
