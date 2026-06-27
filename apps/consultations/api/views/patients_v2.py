import csv
import logging
from django.http import StreamingHttpResponse
from django.utils import timezone
from django.db.models import Q, Value, Count
from django.db.models.functions import Concat
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination

from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.models import Patient
from apps.consultations.services.patient_service import PatientService
from apps.consultations.api.serializers.patients_v2 import (
    PatientListSerializer,
    PatientDetailSerializer,
    PatientCreateSerializer,
    PatientUpdateSerializer,
    PatientBulkActionSerializer,
)

logger = logging.getLogger(__name__)

class PatientPagination(PageNumberPagination):
    """
    Standard pagination for patients list.
    """
    page_size = 10
    max_page_size = 100
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        total_pages = self.page.paginator.num_pages if self.page else 0
        current_page = self.page.number if self.page else 1
        page_size = self.get_page_size(self.request)

        return success_response(
            message="Patients fetched successfully.",
            data={
                "results": data,
                "pagination": {
                    'count': self.page.paginator.count,
                    'page': current_page,
                    'page_size': page_size,
                    'total_pages': total_pages,
                    'next': self.get_next_link(),
                    'previous': self.get_previous_link(),
                }
            }
        )


class PatientPermission(permissions.BasePermission):
    """
    Role-based access controls for Patient Management.
    - ADMIN: Full access (list, retrieve, create, update, delete/archive, bulk, export, stats).
    - RECEPTIONIST: View, Create, Update. No Delete/Archive.
    - DOCTOR: View only (list, retrieve, stats, preview, search, export). No Create, Update, Delete.
    """
    def has_permission(self, request, view) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False

        # Verify role exists
        if not request.user.has_any_role(['ADMIN', 'RECEPTIONIST', 'DOCTOR']):
            return False

        # Read operations are allowed for all 3 roles
        if request.method in permissions.SAFE_METHODS:
            return True

        # Delete operations are restricted to ADMIN only
        if request.method == 'DELETE':
            return request.user.has_role('ADMIN')

        # Create/Update operations allowed for ADMIN & RECEPTIONIST
        if request.method in ['POST', 'PUT', 'PATCH']:
            # For viewset actions, check specific custom endpoint permissions
            if view.action == 'bulk_actions':
                action_type = request.data.get('action')
                if action_type == 'archive':
                    return request.user.has_role('ADMIN')
                return request.user.has_any_role(['ADMIN', 'RECEPTIONIST'])
            
            return request.user.has_any_role(['ADMIN', 'RECEPTIONIST'])

        return False


class Echo:
    """
    Implements write method to allow streaming CSV formatting on the fly.
    """
    def write(self, value):
        return value


class PatientViewSet(viewsets.ModelViewSet):
    """
    Unified ViewSet managing the Patients Module APIs.
    """
    queryset = Patient.objects.filter(is_deleted=False)
    permission_classes = [PatientPermission]
    pagination_class = PatientPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return PatientCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return PatientUpdateSerializer
        elif self.action == 'retrieve':
            return PatientDetailSerializer
        elif self.action == 'bulk_actions':
            return PatientBulkActionSerializer
        return PatientListSerializer

    def list(self, request, *args, **kwargs):
        """
        API 2: Patients List
        """
        queryset = PatientService.list_patients(request.query_params)
        
        paginator = self.pagination_class()
        try:
            page = paginator.paginate_queryset(queryset, request, view=self)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.warning(f"Patient list pagination failed: {str(e)}")
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def retrieve(self, request, *args, **kwargs):
        """
        API 3: Patient Details
        """
        try:
            patient = self.get_object()
        except Exception:
            return error_response(
                message="Patient not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
            
        serializer = self.get_serializer(patient)
        return success_response(
            message="Patient details retrieved successfully.",
            data=serializer.data
        )

    def create(self, request, *args, **kwargs):
        """
        API 4: Create Patient (Manual Registration)
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        ip_address = get_client_ip(request)

        try:
            patient = PatientService.create_patient(
                validated_data=serializer.validated_data,
                user=request.user,
                ip_address=ip_address
            )
            
            # Serialize for detail response
            detail_serializer = PatientDetailSerializer(patient)
            return success_response(
                message="Patient registered successfully.",
                data=detail_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            if hasattr(e, 'detail'):
                raise e
            logger.error(f"Error registering patient manually: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def partial_update(self, request, *args, **kwargs):
        """
        API 5: Update Patient
        """
        try:
            patient = self.get_object()
        except Exception:
            return error_response(
                message="Patient not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        serializer = self.get_serializer(patient, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        ip_address = get_client_ip(request)

        try:
            updated_patient = PatientService.update_patient(
                patient=patient,
                validated_data=serializer.validated_data,
                user=request.user,
                ip_address=ip_address
            )
            detail_serializer = PatientDetailSerializer(updated_patient)
            return success_response(
                message="Patient profile updated successfully.",
                data=detail_serializer.data
            )
        except Exception as e:
            if hasattr(e, 'detail'):
                raise e
            logger.error(f"Error updating patient profile: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    def destroy(self, request, *args, **kwargs):
        """
        API 6: Delete Patient (Soft Delete)
        """
        try:
            patient = self.get_object()
        except Exception:
            return error_response(
                message="Patient not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        ip_address = get_client_ip(request)
        
        try:
            PatientService.soft_delete_patient(
                patient=patient,
                user=request.user,
                ip_address=ip_address
            )
            return success_response(
                message="Patient archived successfully."
            )
        except Exception as e:
            logger.error(f"Error archiving patient: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        API 1: Patient Statistics
        """
        try:
            stats = PatientService.get_patient_statistics()
            return success_response(
                message="Patient statistics loaded successfully.",
                data=stats
            )
        except Exception as e:
            logger.error(f"Error loading patient statistics: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='filter-options')
    def filter_options(self, request):
        """
        API 7: Patient Filters Metadata
        """
        try:
            options = PatientService.get_filter_options()
            return success_response(
                message="Filter options retrieved successfully.",
                data=options
            )
        except Exception as e:
            logger.error(f"Error fetching filter options: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'])
    def search(self, request):
        """
        API 8: Patient Quick Search (Autocomplete, limit 10)
        """
        search_query = request.query_params.get('search', '').strip()
        
        # Base query excluding deleted
        queryset = Patient.objects.filter(is_deleted=False)

        if search_query:
            # Annotate full child & parent names
            queryset = queryset.annotate(
                patient_name=Concat('child_first_name', Value(' '), 'child_last_name'),
                parent_name=Concat('parent_first_name', Value(' '), 'parent_last_name')
            ).filter(
                Q(patient_number__icontains=search_query) |
                Q(patient_name__icontains=search_query) |
                Q(parent_name__icontains=search_query) |
                Q(mobile_number__icontains=search_query)
            )

        # Limit to 10 records for quick autocomplete
        queryset = queryset.order_by('child_last_name', 'child_first_name')[:10]
        
        serializer = PatientListSerializer(queryset, many=True)
        return success_response(
            message="Autocomplete search completed successfully.",
            data=serializer.data
        )

    @action(detail=False, methods=['get'])
    def export(self, request):
        """
        API 9: Export Patients (CSV Streaming)
        """
        queryset = PatientService.list_patients(request.query_params)
        
        # Log export action
        ip_address = get_client_ip(request)
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.PATIENT_EXPORTED,
            description="Patient list exported to CSV.",
            ip_address=ip_address
        )

        pseudo_buffer = Echo()
        writer = csv.writer(pseudo_buffer)

        def csv_iterator():
            # Header Row
            yield writer.writerow([
                'Patient ID', 'Child Name', 'Gender', 'Date of Birth',
                'Parent Name', 'Relationship', 'Mobile Number', 'Email',
                'Status', 'Assigned Doctor', 'Created At'
            ])

            # Chunked iteration to scale up to 100,000+ patient records safely
            for patient in queryset.iterator(chunk_size=1000):
                child_name = f"{patient.child_first_name} {patient.child_last_name}"
                parent_name = f"{patient.parent_first_name} {patient.parent_last_name}"
                doctor_name = f"Dr. {patient.assigned_doctor.first_name} {patient.assigned_doctor.last_name}" if patient.assigned_doctor else "None"
                created_date = patient.created_at.strftime('%Y-%m-%d %H:%M:%S') if patient.created_at else "N/A"

                yield writer.writerow([
                    patient.patient_number,
                    child_name,
                    patient.gender,
                    str(patient.date_of_birth),
                    parent_name,
                    patient.get_relationship_to_child_display(),
                    patient.mobile_number,
                    patient.email,
                    patient.get_patient_status_display(),
                    doctor_name,
                    created_date
                ])

        response = StreamingHttpResponse(csv_iterator(), content_type="text/csv")
        response['Content-Disposition'] = 'attachment; filename="patients_export.csv"'
        return response

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """
        API 10: Patient Summary Chart (Status Breakdown)
        """
        try:
            breakdown = Patient.objects.filter(is_deleted=False).values('patient_status').annotate(
                count=Count('id')
            )
            
            # Map choice codes to readable names
            summary_dict = {
                "Under Treatment": 0,
                "Completed": 0,
                "Inactive": 0,
                "Active": 0
            }
            
            for item in breakdown:
                status_code = item['patient_status']
                count = item['count']
                if status_code == 'UNDER_TREATMENT':
                    summary_dict["Under Treatment"] = count
                elif status_code == 'DISCHARGED':
                    summary_dict["Completed"] = count
                elif status_code == 'INACTIVE':
                    summary_dict["Inactive"] = count
                elif status_code == 'ACTIVE':
                    summary_dict["Active"] = count
                elif status_code == 'FOLLOW_UP':
                    summary_dict["Active"] += count # follow up counts towards active

            return success_response(
                message="Patient status breakdown summary retrieved.",
                data=summary_dict
            )
        except Exception as e:
            logger.error(f"Error calculating patient status summary: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='bulk-actions')
    def bulk_actions(self, request):
        """
        API 11: Bulk Actions
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_ids = serializer.validated_data.get('patient_ids')
        action_name = serializer.validated_data.get('action')
        doctor_id = serializer.validated_data.get('doctor_id')
        
        ip_address = get_client_ip(request)

        try:
            result = PatientService.perform_bulk_action(
                patient_ids=patient_ids,
                action=action_name,
                extra_data={"doctor_id": doctor_id},
                user=request.user,
                ip_address=ip_address
            )
            return success_response(
                message=result["message"],
                data={"affected_count": result["affected_count"]}
            )
        except Exception as e:
            if hasattr(e, 'detail'):
                raise e
            logger.error(f"Bulk action failed: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['get'])
    def recent(self, request):
        """
        API 12: Recent Patients
        """
        try:
            queryset = Patient.objects.filter(is_deleted=False).annotate(
                patient_name=Concat('child_first_name', Value(' '), 'child_last_name'),
                parent_name=Concat('parent_first_name', Value(' '), 'parent_last_name')
            ).order_by('-created_at')[:10]
            
            serializer = PatientListSerializer(queryset, many=True)
            return success_response(
                message="Recently registered patients retrieved.",
                data=serializer.data
            )
        except Exception as e:
            logger.error(f"Error fetching recent patients: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
