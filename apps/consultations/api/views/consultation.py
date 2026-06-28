from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.utils.decorators import method_decorator

from apps.consultations.api.permissions import IsDoctorWriteOrAdminOrReceptionistReadOnly
from apps.consultations.services.consultation_service import ConsultationService
from apps.consultations.api.serializers.consultation import (
    ConsultationSerializer,
    ConsultationAttachmentSerializer,
    PatientSummaryResponseSerializer,
    ConsultationHistorySerializer
)
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class ConsultationAppointmentDetailAPIView(APIView):
    """
    get:
    Summary: Open Consultation Session
    Description:
      Retrieves all clinical data required to start or view a consultation session.
      Includes appointment details, patient summary, medical history, and previous visits.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Admins/Receptionists get Read-only; Doctors must be assigned)
      
    Responses:
      200: Successfully retrieved session data.
      403: If logged in doctor is not the doctor assigned to this appointment.
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, appointment_id):
        data = ConsultationService.get_open_consultation_data(
            user=request.user,
            appointment_id=appointment_id
        )
        
        # Serialize the complex response
        serialized_appointment = {
            "id": str(data["appointment"].id),
            "appointment_number": data["appointment"].appointment_number,
            "appointment_type": data["appointment"].appointment_type,
            "appointment_date": data["appointment"].appointment_date,
            "status": data["appointment"].status,
        }
        
        serialized_prev_consultations = ConsultationHistorySerializer(data["previous_consultations"], many=True).data
        serialized_followups = ConsultationHistorySerializer(data["followups"], many=True).data
        
        response_data = {
            "appointment": serialized_appointment,
            "patient_summary": data["patient_summary"],
            "medical_history": data["medical_history"],
            "previous_consultations": serialized_prev_consultations,
            "followups": serialized_followups,
            "appointment_information": data["appointment_information"]
        }
        
        return success_response(
            message="Consultation session data loaded successfully.",
            data=response_data
        )


class PatientSummaryAPIView(APIView):
    """
    get:
    Summary: Retrieve Patient Summary Dashboard
    Description:
      Returns a concise overview of the patient's profile, parent info, derived age,
      previous diagnoses, current treatment, and total visits.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, patient_id):
        data = ConsultationService.get_patient_summary(patient_id=patient_id)
        return success_response(
            message="Patient summary retrieved successfully.",
            data=data
        )


class PreviousConsultationsAPIView(APIView):
    """
    get:
    Summary: Retrieve Previous Consultations History
    Description:
      Returns a paginated, searchable, and sortable history of completed consultations.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly
      
    Query Parameters:
      - search: Search text for diagnosis, treatment notes, recommendations, or doctor email.
      - ordering: Field to order by (e.g. 'created_at' or '-created_at').
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]
    pagination_class = StandardResultsSetPagination

    def get(self, request, patient_id):
        search_query = request.query_params.get("search")
        ordering = request.query_params.get("ordering")
        
        queryset = ConsultationService.get_previous_consultations(
            patient_id=patient_id,
            search_query=search_query,
            ordering=ordering
        )
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)
        if page is not None:
            serializer = ConsultationHistorySerializer(page, many=True)
            return paginator.get_paginated_response(serializer.data)

        serializer = ConsultationHistorySerializer(queryset, many=True)
        return success_response(
            message="Consultation history retrieved successfully.",
            data=serializer.data
        )


class FollowupHistoryAPIView(APIView):
    """
    get:
    Summary: Retrieve Follow-up Consultations History
    Description:
      Returns a list of all completed follow-up consultations.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, patient_id):
        queryset = ConsultationService.get_followup_history(patient_id=patient_id)
        serializer = ConsultationHistorySerializer(queryset, many=True)
        return success_response(
            message="Follow-up history retrieved successfully.",
            data=serializer.data
        )


class ConsultationCreateAPIView(APIView):
    """
    post:
    Summary: Create Consultation Record
    Description:
      Creates an active consultation record for an appointment.
      Transition timeline, validates field lengths, and registers activity/audit logs.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Write restricted to Doctor)
      
    Request Body:
      - appointment_id: UUID (Required)
      - chief_complaint: String (Max 2000 chars)
      - clinical_findings: String (Max 10000 chars)
      - diagnosis: String (Max 3000 chars)
      - treatment_notes: String (Max 10000 chars)
      - recommendations: String (Max 5000 chars)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request):
        ip_address = get_client_ip(request)
        appointment_id = request.data.get("appointment_id")
        
        if not appointment_id:
            return success_response(
                message="appointment_id is required.",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
            
        consultation = ConsultationService.create_consultation(
            user=request.user,
            ip_address=ip_address,
            appointment_id=appointment_id,
            data=request.data
        )
        
        serializer = ConsultationSerializer(consultation)
        return success_response(
            message="Consultation record created successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class ConsultationUpdateAPIView(APIView):
    """
    patch:
    Summary: Update Consultation Record
    Description:
      Edits fields on an active, uncompleted consultation record.
      Tracks changes and saves field-level audit logs.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Write restricted to Doctor)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def patch(self, request, consultation_id):
        ip_address = get_client_ip(request)
        consultation = ConsultationService.update_consultation(
            user=request.user,
            ip_address=ip_address,
            consultation_id=consultation_id,
            data=request.data
        )
        
        serializer = ConsultationSerializer(consultation)
        return success_response(
            message="Consultation record updated successfully.",
            data=serializer.data
        )


class ConsultationAttachmentListUploadAPIView(APIView):
    """
    get:
    Summary: List Consultation Attachments
    Description:
      Returns all active, non-deleted attachments uploaded for this consultation.
      
    post:
    Summary: Upload Clinical Documents
    Description:
      Uploads one or more supporting clinical documents (PDF, DOC, DOCX, PNG, JPG, JPEG, WEBP).
      Rejects executable formats, files exceeding 20MB, or non-allowed extensions.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Write restricted to Doctor)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def get(self, request, consultation_id):
        attachments = ConsultationService.list_attachments(
            user=request.user,
            consultation_id=consultation_id
        )
        serializer = ConsultationAttachmentSerializer(attachments, many=True)
        return success_response(
            message="Attachments retrieved successfully.",
            data=serializer.data
        )

    def post(self, request, consultation_id):
        ip_address = get_client_ip(request)
        
        # Support multiple file uploads
        files = request.FILES.getlist("files")
        if not files:
            # Fallback if uploaded under a single 'file' key
            single_file = request.FILES.get("file")
            if single_file:
                files = [single_file]
                
        if not files:
            return success_response(
                message="No files provided for upload.",
                status_code=status.HTTP_400_BAD_REQUEST,
                success=False
            )
            
        attachments = ConsultationService.upload_attachments(
            user=request.user,
            ip_address=ip_address,
            consultation_id=consultation_id,
            files=files
        )
        
        serializer = ConsultationAttachmentSerializer(attachments, many=True)
        return success_response(
            message="Documents uploaded successfully.",
            data=serializer.data,
            status_code=status.HTTP_201_CREATED
        )


class ConsultationAttachmentDeleteAPIView(APIView):
    """
    delete:
    Summary: Delete Attachment
    Description:
      Soft-deletes a consultation attachment.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Write restricted to Doctor)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def delete(self, request, consultation_id, attachment_id):
        ip_address = get_client_ip(request)
        ConsultationService.delete_attachment(
            user=request.user,
            ip_address=ip_address,
            consultation_id=consultation_id,
            attachment_id=attachment_id
        )
        return success_response(
            message="Attachment deleted successfully."
        )


class ConsultationCompleteAPIView(APIView):
    """
    post:
    Summary: Complete Clinical Consultation
    Description:
      Locks the consultation record. Transitions the parent appointment status to COMPLETED.
      Requires diagnosis, treatment notes, and recommendations to be present.
      
    Permissions:
      - IsAuthenticated
      - IsDoctorWriteOrAdminOrReceptionistReadOnly (Write restricted to Doctor)
    """
    permission_classes = [IsAuthenticated, IsDoctorWriteOrAdminOrReceptionistReadOnly]

    def post(self, request, consultation_id):
        ip_address = get_client_ip(request)
        consultation = ConsultationService.complete_consultation(
            user=request.user,
            ip_address=ip_address,
            consultation_id=consultation_id
        )
        
        serializer = ConsultationSerializer(consultation)
        return success_response(
            message="Consultation completed and locked successfully.",
            data=serializer.data
        )
