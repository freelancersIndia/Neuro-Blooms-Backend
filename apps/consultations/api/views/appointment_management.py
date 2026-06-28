from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status, serializers
from django.db.models import Q

from apps.consultations.api.permissions import IsAdminOrReceptionistOrDoctorReadOnly, IsDoctorOrAdminOrReceptionist
from apps.consultations.api.serializers.appointment_management import (
    AppointmentRequestApproveSerializer,
    AppointmentRequestRejectSerializer,
    AppointmentRequestRescheduleSerializer,
    AppointmentUpdateSerializer,
    AppointmentRescheduleSerializer,
    AppointmentCancelSerializer,
    AppointmentDetailSerializer
)
from apps.consultations.api.views.appointment import AppointmentBookingAPIView
from apps.consultations.models import Appointment, AppointmentRequest, PatientTimeline
from apps.consultations.services.appointment_service import AppointmentService
from apps.consultations.services.patient_matching_service import PatientMatchingService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class AppointmentRequestDetailSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    appointment_type_display = serializers.CharField(source="get_appointment_type_display", read_only=True)
    match_result = serializers.SerializerMethodField()
    timeline = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentRequest
        fields = [
            "id",
            "request_number",
            "parent_first_name",
            "parent_last_name",
            "relationship_to_child",
            "mobile_number",
            "alternate_mobile_number",
            "email",
            "child_first_name",
            "child_last_name",
            "date_of_birth",
            "gender",
            "appointment_type",
            "appointment_type_display",
            "primary_concern",
            "preferred_date",
            "preferred_time_slot",
            "additional_notes",
            "referral_source",
            "booking_source",
            "status",
            "status_display",
            "rejection_reason",
            "reviewed_by",
            "reviewed_at",
            "patient",
            "patient_name",
            "patient_linked_by",
            "patient_linked_at",
            "patient_created_by",
            "patient_created_at",
            "match_result",
            "timeline"
        ]

    def get_patient_name(self, obj):
        if obj.patient:
            return f"{obj.patient.child_first_name} {obj.patient.child_last_name}"
        return None

    def get_match_result(self, obj):
        try:
            return PatientMatchingService.find_matches(obj.id)
        except Exception:
            return None

    def get_timeline(self, obj):
        if obj.patient:
            events = PatientTimeline.objects.filter(patient=obj.patient).order_by("created_at")
            return [
                {
                    "event": event.event,
                    "description": event.description,
                    "performed_by_email": event.performed_by.email if event.performed_by else None,
                    "created_at": event.created_at
                }
                for event in events
            ]
        return []


class AppointmentRequestDetailAPIView(APIView):
    """
    get:
    Summary: Retrieve Appointment Request
    Description:
      Retrieves the full details of an Appointment Request, including the linked patient,
      preferred slot, match results, and patient timeline.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly
      
    Example Request:
      GET /api/v1/appointment-requests/d3b07384-d113-4956-a5d8-472d7d56637e/
      
    Example Response:
      {
        "success": true,
        "message": "Appointment request retrieved.",
        "data": {
          "id": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "request_number": "REQ-2026-00001",
          "parent_first_name": "Ravi",
          ...
          "match_result": { ... },
          "timeline": [ ... ]
        }
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request, id):
        request_obj = AppointmentRequest.objects.filter(id=id).first()
        if not request_obj:
            return success_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        serializer = AppointmentRequestDetailSerializer(request_obj)
        return success_response(
            message="Appointment request retrieved.",
            data=serializer.data
        )


class AppointmentRequestApproveAPIView(APIView):
    """
    post:
    Summary: Approve Appointment Request
    Description:
      Approves an appointment request, validates the slot and doctor availability, and automatically
      creates a confirmed appointment.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
      
    Request Schema:
      - doctor_id (UUID, Required)
      - appointment_date (Date, Required, e.g., "2026-07-20")
      - start_time (Time, Required, e.g., "10:30")
      - remarks (String, Optional)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        serializer = AppointmentRequestApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        appointment = AppointmentService.approve_request(
            user=request.user,
            ip_address=ip_address,
            request_id=id,
            doctor_id=serializer.validated_data["doctor_id"],
            appointment_date=serializer.validated_data["appointment_date"],
            start_time=serializer.validated_data["start_time"],
            remarks=serializer.validated_data.get("remarks", "")
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment request approved successfully.",
            data=detail_serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class AppointmentRequestRejectAPIView(APIView):
    """
    post:
    Summary: Reject Appointment Request
    Description:
      Rejects an appointment request. Requires a mandatory reason.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        serializer = AppointmentRequestRejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        AppointmentService.reject_request(
            user=request.user,
            ip_address=ip_address,
            request_id=id,
            reason=serializer.validated_data["reason"]
        )

        return success_response(
            message="Appointment request rejected successfully."
        )


class AppointmentRequestRescheduleAPIView(APIView):
    """
    post:
    Summary: Reschedule Appointment Request
    Description:
      Moves the preferred slot of an appointment request.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        serializer = AppointmentRequestRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        AppointmentService.reschedule_request(
            user=request.user,
            ip_address=ip_address,
            request_id=id,
            doctor_id=serializer.validated_data["doctor_id"],
            appointment_date=serializer.validated_data["appointment_date"],
            start_time=serializer.validated_data["start_time"],
            reason=serializer.validated_data.get("reason", "")
        )

        return success_response(
            message="Appointment request rescheduled successfully."
        )


class AppointmentListAPIView(APIView):
    """
    get:
    Summary: List Appointments
    Description:
      Returns a paginated list of active appointments with support for search, filters, and sorting.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly
      
    post:
    Summary: Book Appointment
    Description:
      Creates a confirmed appointment using an available slot.
      Delegates to AppointmentBookingAPIView.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request):
        queryset = Appointment.objects.filter(is_active=True)

        # Filters
        doctor_id = request.query_params.get("doctor")
        if doctor_id:
            queryset = queryset.filter(doctor_id=doctor_id)

        patient_id = request.query_params.get("patient")
        if patient_id:
            queryset = queryset.filter(patient_id=patient_id)

        date_val = request.query_params.get("date")
        if date_val:
            queryset = queryset.filter(appointment_date=date_val)

        status_val = request.query_params.get("status")
        if status_val:
            queryset = queryset.filter(status=status_val)

        appt_type = request.query_params.get("appointment_type")
        if appt_type:
            queryset = queryset.filter(appointment_type=appt_type)

        # Search
        search_query = request.query_params.get("search")
        if search_query:
            queryset = queryset.filter(
                Q(appointment_number__icontains=search_query) |
                Q(patient__child_first_name__icontains=search_query) |
                Q(patient__child_last_name__icontains=search_query) |
                Q(patient__patient_number__icontains=search_query) |
                Q(doctor__first_name__icontains=search_query) |
                Q(doctor__last_name__icontains=search_query) |
                Q(doctor__email__icontains=search_query)
            )

        # Ordering
        ordering = request.query_params.get("ordering")
        if ordering:
            order_fields = [f.strip() for f in ordering.split(",") if f.strip()]
            queryset = queryset.order_by(*order_fields)
        else:
            queryset = queryset.order_by("-appointment_date", "-start_time")

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        
        serializer = AppointmentDetailSerializer(page, many=True)
        paginated_data = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }

        return success_response(
            message="Appointments retrieved successfully.",
            data=paginated_data
        )

    def post(self, request):
        return AppointmentBookingAPIView().post(request)


class AppointmentDetailAPIView(APIView):
    """
    get:
    Summary: Retrieve Appointment Details
    Description:
      Retrieves the full details of an Appointment, including patient, doctor, and timeline.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly

    patch:
    Summary: Edit Appointment
    Description:
      Edits fields on an existing confirmed appointment. Re-runs slot validation if doctor/date/time changes.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request, id):
        appointment = Appointment.objects.filter(id=id, is_active=True).first()
        if not appointment:
            return success_response(
                message="Appointment not found.",
                status_code=status.HTTP_404_NOT_FOUND,
                success=False
            )
        serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment retrieved.",
            data=serializer.data
        )

    def patch(self, request, id):
        serializer = AppointmentUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        appointment = AppointmentService.update_appointment(
            user=request.user,
            ip_address=ip_address,
            appointment_id=id,
            data=serializer.validated_data
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment updated successfully.",
            data=detail_serializer.data
        )


class AppointmentRescheduleAPIView(APIView):
    """
    post:
    Summary: Reschedule Confirmed Appointment
    Description:
      Moves a confirmed appointment to a new date and time.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        serializer = AppointmentRescheduleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        appointment = AppointmentService.reschedule_appointment(
            user=request.user,
            ip_address=ip_address,
            appointment_id=id,
            appointment_date=serializer.validated_data["appointment_date"],
            start_time=serializer.validated_data["start_time"],
            reason=serializer.validated_data.get("reason", "")
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment rescheduled successfully.",
            data=detail_serializer.data
        )


class AppointmentCancelAPIView(APIView):
    """
    post:
    Summary: Cancel Appointment
    Description:
      Cancels a confirmed appointment. Releasing the booked slot automatically.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        serializer = AppointmentCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        appointment = AppointmentService.cancel_appointment(
            user=request.user,
            ip_address=ip_address,
            appointment_id=id,
            reason=serializer.validated_data["reason"]
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment cancelled successfully.",
            data=detail_serializer.data
        )


class AppointmentCheckInAPIView(APIView):
    """
    post:
    Summary: Check-in Patient
    Description:
      Checks in the patient upon arrival. Transitions status to CHECKED_IN.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        ip_address = get_client_ip(request)
        appointment = AppointmentService.check_in_appointment(
            user=request.user,
            ip_address=ip_address,
            appointment_id=id
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Patient checked in successfully.",
            data=detail_serializer.data
        )


class AppointmentStartConsultationAPIView(APIView):
    """
    post:
    Summary: Start Doctor Consultation
    Description:
      Transitions appointment status to IN_CONSULTATION. Can only be performed by the assigned Doctor.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Doctors)
    """
    permission_classes = [IsAuthenticated, IsDoctorOrAdminOrReceptionist]

    def post(self, request, id):
        ip_address = get_client_ip(request)
        appointment = AppointmentService.start_consultation(
            user=request.user,
            ip_address=ip_address,
            appointment_id=id
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Consultation started successfully.",
            data=detail_serializer.data
        )


class AppointmentMarkNoShowAPIView(APIView):
    """
    post:
    Summary: Mark No Show
    Description:
      Marks the patient as a no-show. Transitions status to NO_SHOW.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Write restricted to Admins/Receptionists)
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request, id):
        ip_address = get_client_ip(request)
        appointment = AppointmentService.mark_no_show(
            user=request.user,
            ip_address=ip_address,
            appointment_id=id
        )

        detail_serializer = AppointmentDetailSerializer(appointment)
        return success_response(
            message="Appointment marked as no-show successfully.",
            data=detail_serializer.data
        )
