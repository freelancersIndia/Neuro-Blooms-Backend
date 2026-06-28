from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.pagination import PageNumberPagination
from rest_framework import status
from django.db.models import Q

from apps.consultations.api.permissions import IsAdminOrReceptionistOrDoctorReadOnly
from apps.consultations.api.serializers.patient_matching import (
    PatientMatchingQuerySerializer,
    PatientLinkSerializer,
    PatientCreateSerializer,
    PatientSearchQuerySerializer,
    PatientSearchResultSerializer
)
from apps.consultations.models.patient import Patient
from apps.consultations.services.patient_matching_service import PatientMatchingService
from apps.accounts.utils.responses import success_response
from apps.accounts.utils.ip import get_client_ip

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class PatientMatchingAPIView(APIView):
    """
    get:
    Summary: Automatically Search Existing Patients (Matching)
    Description:
      Retrieves the specified Appointment Request and calculates matching patients
      using a weighted scoring algorithm to prevent duplicate records.
    
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Super Admin, Admin, and Receptionist get Full Access; Doctor gets Read-Only)
      
    Query Parameters:
      - request_id (UUID, Required): ID of the Appointment Request to match.
      
    Validation Rules:
      - Appointment Request must exist.
      
    Business Rules:
      - Compares the request details against existing patients based on:
        - Mobile Number (50%)
        - Child Name (20% - 10% first name, 10% last name)
        - Parent Name (15% - 7.5% first name, 7.5% last name)
        - Date of Birth (10%)
        - Gender (5%)
      - Returns matches with a score of 60% or higher, sorted by score descending.
      - Never automatically creates or links a patient.
      
    Example Request:
      GET /api/v1/patient-matching/?request_id=d3b07384-d113-4956-a5d8-472d7d56637e
      
    Example Response:
      {
        "success": true,
        "message": "Patient matches retrieved successfully.",
        "data": {
          "request_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
          "total_matches": 1,
          "matches": [
            {
              "patient_id": "8a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
              "patient_code": "PAT-000014",
              "child_name": "Aarav Kumar",
              "parent_name": "Ravi Kumar",
              "mobile_number": "9876543210",
              "match_score": 96,
              "match_level": "EXACT_MATCH",
              "matched_fields": ["mobile_number", "child_name", "date_of_birth"]
            }
          ]
        }
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request):
        serializer = PatientMatchingQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        request_id = serializer.validated_data["request_id"]
        result = PatientMatchingService.find_matches(request_id)

        return success_response(
            message="Patient matches retrieved successfully.",
            data=result
        )


class PatientMatchDetailsAPIView(APIView):
    """
    get:
    Summary: View Match Details
    Description:
      Provides a detailed field-by-field comparison explaining why a patient was matched
      against an appointment request.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Super Admin, Admin, and Receptionist get Full Access; Doctor gets Read-Only)
      
    Query Parameters:
      - request_id (UUID, Required): ID of the Appointment Request.
      
    Validation/Business Rules:
      - Both Appointment Request and Patient must exist.
      
    Example Request:
      GET /api/v1/patient-matching/8a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d/details/?request_id=d3b07384-d113-4956-a5d8-472d7d56637e
      
    Example Response:
      {
        "success": true,
        "message": "Match details retrieved successfully.",
        "data": {
          "match_score": 96,
          "matched_fields": [
            {
              "field": "mobile_number",
              "request_value": "9876543210",
              "patient_value": "9876543210",
              "matched": true
            },
            {
              "field": "child_name",
              "request_value": "Aarav Kumar",
              "patient_value": "Aarav Kumar",
              "matched": true
            },
            {
              "field": "parent_name",
              "request_value": "Ravi Kumar",
              "patient_value": "Ravi Kumar",
              "matched": true
            },
            {
              "field": "date_of_birth",
              "request_value": "2020-01-01",
              "patient_value": "2020-01-01",
              "matched": true
            },
            {
              "field": "gender",
              "request_value": "MALE",
              "patient_value": "MALE",
              "matched": true
            }
          ]
        }
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request, patient_id):
        serializer = PatientMatchingQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        request_id = serializer.validated_data["request_id"]
        result = PatientMatchingService.get_match_details(request_id, patient_id)

        return success_response(
            message="Match details retrieved successfully.",
            data=result
        )


class PatientLinkAPIView(APIView):
    """
    post:
    Summary: Link Existing Patient
    Description:
      Attaches an Appointment Request to an existing active patient.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Super Admin, Admin, and Receptionist get Full Access; Doctor gets Read-Only)
      
    Request Schema (JSON):
      - request_id (UUID, Required): ID of the Appointment Request.
      - patient_id (UUID, Required): ID of the Patient to link.
      
    Validation/Business Rules:
      - Appointment Request and Patient must exist.
      - Request status must be PENDING or APPROVED.
      - Cannot link twice.
      - Automatically transitions request status to PATIENT_LINKED.
      - Automatically records PatientTimeline entries ("Patient Matching Started", "Patient Linked").
      - Creates Activity Log.
      
    Example Request:
      POST /api/v1/patient-matching/link/
      {
        "request_id": "d3b07384-d113-4956-a5d8-472d7d56637e",
        "patient_id": "8a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d"
      }
      
    Example Response:
      {
        "success": true,
        "message": "Patient linked successfully."
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request):
        serializer = PatientLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        PatientMatchingService.link_patient(
            user=request.user,
            ip_address=ip_address,
            request_id=serializer.validated_data["request_id"],
            patient_id=serializer.validated_data["patient_id"]
        )

        return success_response(
            message="Patient linked successfully."
        )


class PatientCreateAPIView(APIView):
    """
    post:
    Summary: Create New Patient from Request
    Description:
      Converts an Appointment Request into a new Patient record.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Super Admin, Admin, and Receptionist get Full Access; Doctor gets Read-Only)
      
    Request Schema (JSON):
      - request_id (UUID, Required): ID of the Appointment Request.
      
    Validation/Business Rules:
      - Appointment Request must exist.
      - Request status must be PENDING or APPROVED.
      - Executes the matching algorithm again immediately before creation to ensure no exact duplicate (score >= 95) exists.
      - Automatically copies child and parent details, contact info, and medical history (primary concern).
      - Generates a unique patient code (e.g., PAT-000245).
      - Transitions request status to PATIENT_CREATED.
      - Records PatientTimeline entries ("Patient Matching Started", "New Patient Created").
      - Creates Activity Log.
      
    Example Request:
      POST /api/v1/patient-matching/create-patient/
      {
        "request_id": "d3b07384-d113-4956-a5d8-472d7d56637e"
      }
      
    Example Response:
      {
        "success": true,
        "message": "Patient created successfully.",
        "data": {
          "id": "8a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
          "patient_number": "PAT-000245",
          "child_name": "Aarav Kumar"
        }
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def post(self, request):
        serializer = PatientCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        ip_address = get_client_ip(request)
        patient = PatientMatchingService.create_patient(
            user=request.user,
            ip_address=ip_address,
            request_id=serializer.validated_data["request_id"]
        )

        return success_response(
            message="Patient created successfully.",
            data={
                "id": patient.id,
                "patient_number": patient.patient_number,
                "child_name": f"{patient.child_first_name} {patient.child_last_name}"
            },
            status_code=status.HTTP_201_CREATED
        )


class PatientMatchingStatisticsAPIView(APIView):
    """
    get:
    Summary: Patient Matching Statistics
    Description:
      Retrieves today's patient matching and creation statistics.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Super Admin, Admin, and Receptionist get Full Access; Doctor gets Read-Only)
      
    Example Request:
      GET /api/v1/patient-matching/statistics/
      
    Example Response:
      {
        "success": true,
        "message": "Statistics retrieved successfully.",
        "data": {
          "today_matches": 18,
          "linked_patients": 11,
          "new_patients": 7,
          "duplicate_prevented": 5
        }
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request):
        stats = PatientMatchingService.get_statistics()
        return success_response(
            message="Statistics retrieved successfully.",
            data=stats
        )


class PatientSearchAPIView(APIView):
    """
    get:
    Summary: Manual Patient Search
    Description:
      Allows receptionist or admin to manually search existing patients with pagination.
      
    Permissions:
      - IsAuthenticated
      - IsAdminOrReceptionistOrDoctorReadOnly (Super Admin, Admin, and Receptionist get Full Access; Doctor gets Read-Only)
      
    Query Parameters:
      - search (String, Required): Term to search. Min 2 chars, max 100.
        Matches against Patient ID (code), Child Name, Parent Name, Mobile Number, or Email.
      - page (Integer, Optional): Page number.
      - page_size (Integer, Optional): Number of records per page.
      
    Example Request:
      GET /api/v1/patients/search/?search=Aarav
      
    Example Response:
      {
        "success": true,
        "message": "Patients retrieved successfully.",
        "data": {
          "count": 1,
          "next": null,
          "previous": null,
          "results": [
            {
              "id": "8a8b7c6d-5e4f-3a2b-1c0d-9e8f7a6b5c4d",
              "patient_number": "PAT-000014",
              "parent_first_name": "Ravi",
              "parent_last_name": "Kumar",
              "relationship_to_child": "FATHER",
              "mobile_number": "9876543210",
              "alternate_mobile_number": null,
              "email": "ravi.kumar@test.com",
              "child_first_name": "Aarav",
              "child_last_name": "Kumar",
              "date_of_birth": "2020-01-01",
              "gender": "MALE",
              "address": "",
              "patient_status": "ACTIVE"
            }
          ]
        }
      }
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctorReadOnly]

    def get(self, request):
        serializer = PatientSearchQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)

        search_query = serializer.validated_data["search"]

        # Search filter
        queryset = Patient.objects.filter(is_deleted=False).filter(
            Q(patient_number__icontains=search_query) |
            Q(child_first_name__icontains=search_query) |
            Q(child_last_name__icontains=search_query) |
            Q(parent_first_name__icontains=search_query) |
            Q(parent_last_name__icontains=search_query) |
            Q(mobile_number__icontains=search_query) |
            Q(email__icontains=search_query)
        ).distinct()

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        
        response_serializer = PatientSearchResultSerializer(page, many=True)
        paginated_data = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": response_serializer.data
        }

        return success_response(
            message="Patients retrieved successfully.",
            data=paginated_data
        )
