import logging
from django.db.models import Q, Value, Max
from django.db.models.functions import Concat
from django.utils import timezone
from rest_framework import status, serializers
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated

from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.models import AppointmentRequest, Patient
from apps.consultations.api.permissions import IsAdminOrReceptionist, IsAdminOrReceptionistOrDoctor
from apps.consultations.services.patient_matching_service import PatientMatchingService
from apps.consultations.api.serializers.patient_matching import (
    PatientSearchSerializer,
    PatientPreviewSerializer,
    PatientMatchingScreenSerializer,
    PatientLinkSerializer,
)

logger = logging.getLogger(__name__)

class PatientSearchPagination(PageNumberPagination):
    """
    Pagination configuration for patient search.
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


class PatientMatchingAPIView(APIView):
    """
    API 1: Load the complete Patient Matching screen.
    Requires ADMIN or RECEPTIONIST roles.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request, appointment_request_id, *args, **kwargs):
        ip_address = get_client_ip(request)
        
        # Security: Validate UUID
        try:
            import uuid
            uuid.UUID(str(appointment_request_id))
        except ValueError:
            return error_response(
                message="Invalid request ID format.",
                errors={"appointment_request_id": ["Must be a valid UUID."]},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            screen_data = PatientMatchingService.get_patient_matching_screen_data(
                appointment_request_id=appointment_request_id,
                user=request.user,
                ip_address=ip_address
            )
            serializer = PatientMatchingScreenSerializer(screen_data)
            return success_response(
                message="Patient matching screen data loaded successfully.",
                data=serializer.data
            )
        except Exception as e:
            # Check for standard ValidationError / NotFound from DRF
            if hasattr(e, 'detail'):
                raise e
            logger.error(f"Error loading matching screen: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class PatientSearchAPIView(APIView):
    """
    API 2: Manual Patient Search
    Requires ADMIN, RECEPTIONIST, or DOCTOR roles.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctor]
    pagination_class = PatientSearchPagination

    class QueryParamSerializer(serializers.Serializer):
        search = serializers.CharField(required=False, allow_blank=True)
        search_type = serializers.ChoiceField(
            choices=['PATIENT_ID', 'PARENT_NAME', 'CHILD_NAME', 'PHONE', 'EMAIL'],
            required=False
        )
        ordering = serializers.ChoiceField(
            choices=[
                'patient_name', '-patient_name',
                'created_date', '-created_date',
                'last_visit', '-last_visit',
                'patient_id', '-patient_id'
            ],
            required=False,
            default='-created_date'
        )

        def validate(self, attrs):
            search = attrs.get('search')
            search_type = attrs.get('search_type')
            if search and not search_type:
                raise serializers.ValidationError({"search_type": "This field is required when search query is provided."})
            return attrs

    def get(self, request, *args, **kwargs):
        ip_address = get_client_ip(request)
        
        # Validate query parameters
        query_serializer = self.QueryParamSerializer(data=request.query_params)
        query_serializer.is_valid(raise_exception=True)
        
        search = query_serializer.validated_data.get('search', '').strip()
        search_type = query_serializer.validated_data.get('search_type')
        ordering_param = query_serializer.validated_data.get('ordering', '-created_date')

        # Log search action
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.PATIENT_SEARCHED,
            description=f"Manual patient search performed. Query: '{search}', Type: '{search_type or 'ALL'}'",
            ip_address=ip_address
        )

        # Base QuerySet with optimizations
        queryset = Patient.objects.all()

        # Annotate full names and last visit
        queryset = queryset.annotate(
            patient_name=Concat('child_first_name', Value(' '), 'child_last_name'),
            parent_name=Concat('parent_first_name', Value(' '), 'parent_last_name'),
            last_visit=Max('appointments__appointment_date', filter=Q(appointments__status='COMPLETED'))
        )

        # Apply search filters
        if search and search_type:
            if search_type == 'PATIENT_ID':
                queryset = queryset.filter(patient_number__icontains=search)
            elif search_type == 'PARENT_NAME':
                queryset = queryset.filter(parent_name__icontains=search)
            elif search_type == 'CHILD_NAME':
                queryset = queryset.filter(patient_name__icontains=search)
            elif search_type == 'PHONE':
                queryset = queryset.filter(Q(mobile_number__icontains=search) | Q(alternate_mobile_number__icontains=search))
            elif search_type == 'EMAIL':
                queryset = queryset.filter(email__icontains=search)

        # Apply ordering mapping
        ordering_map = {
            'patient_name': ['child_first_name', 'child_last_name'],
            '-patient_name': ['-child_first_name', '-child_last_name'],
            'created_date': ['created_at'],
            '-created_date': ['-created_at'],
            'last_visit': ['last_visit'],
            '-last_visit': ['-last_visit'],
            'patient_id': ['patient_number'],
            '-patient_id': ['-patient_number']
        }
        
        order_fields = ordering_map.get(ordering_param, ['-created_at'])
        queryset = queryset.order_by(*order_fields)

        # Paginate results
        paginator = self.pagination_class()
        try:
            page = paginator.paginate_queryset(queryset, request, view=self)
            if page is not None:
                serializer = PatientSearchSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.warning(f"Patient search pagination failed: {str(e)}")
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class PatientLinkAPIView(APIView):
    """
    API 3: Link an Existing Patient.
    Requires ADMIN or RECEPTIONIST roles.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, appointment_request_id, *args, **kwargs):
        ip_address = get_client_ip(request)

        # Security: Validate UUID
        try:
            import uuid
            uuid.UUID(str(appointment_request_id))
        except ValueError:
            return error_response(
                message="Invalid request ID format.",
                errors={"appointment_request_id": ["Must be a valid UUID."]},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = PatientLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        patient_number = serializer.validated_data.get('patient_id')

        try:
            result = PatientMatchingService.link_patient(
                appointment_request_id=appointment_request_id,
                patient_number=patient_number,
                user=request.user,
                ip_address=ip_address
            )
            return success_response(
                message=result["message"],
                data=None
            )
        except Exception as e:
            if hasattr(e, 'detail'):
                raise e
            logger.error(f"Error linking patient: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class PatientCreateAPIView(APIView):
    """
    API 4: Create a New Patient from Approved Request.
    Requires ADMIN or RECEPTIONIST roles.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, appointment_request_id, *args, **kwargs):
        ip_address = get_client_ip(request)

        # Security: Validate UUID
        try:
            import uuid
            uuid.UUID(str(appointment_request_id))
        except ValueError:
            return error_response(
                message="Invalid request ID format.",
                errors={"appointment_request_id": ["Must be a valid UUID."]},
                status_code=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = PatientMatchingService.create_patient_from_request(
                appointment_request_id=appointment_request_id,
                user=request.user,
                ip_address=ip_address
            )
            return success_response(
                message=result["message"],
                data=result.get("data"),
                status_code=status.HTTP_201_CREATED
            )
        except Exception as e:
            if hasattr(e, 'detail'):
                raise e
            logger.error(f"Error creating patient from request: {str(e)}", exc_info=True)
            return error_response(
                message=str(e),
                status_code=status.HTTP_400_BAD_REQUEST
            )


class PatientPreviewAPIView(APIView):
    """
    API 5: Open Patient Preview Modal.
    Requires ADMIN, RECEPTIONIST, or DOCTOR roles.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionistOrDoctor]

    def get(self, request, patient_id, *args, **kwargs):
        ip_address = get_client_ip(request)

        # Lookup by UUID (id) or patient number
        try:
            import uuid
            is_uuid = True
            uuid.UUID(str(patient_id))
        except ValueError:
            is_uuid = False

        try:
            if is_uuid:
                patient = Patient.objects.get(id=patient_id)
            else:
                patient = Patient.objects.get(patient_number=patient_id)
        except Patient.DoesNotExist:
            return error_response(
                message="Patient not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Log viewing preview
        ActivityLog.objects.create(
            user=request.user,
            action=ActivityType.PATIENT_PREVIEW_VIEWED,
            description=f"Patient preview viewed. Patient ID: {patient.patient_number}",
            ip_address=ip_address
        )

        serializer = PatientPreviewSerializer(patient)
        return success_response(
            message="Patient preview loaded successfully.",
            data=serializer.data
        )
