from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from django.http import HttpResponse

from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.utils.ip import get_client_ip
from apps.accounts.models.user import User
from apps.consultations.models import AppointmentRequest, Patient
from apps.consultations.api.permissions import IsAdminOrReceptionist
from apps.consultations.api.views.appointment_management import StandardResultsSetPagination
from apps.consultations.api.serializers.booking import AppointmentRequestPublicCreateSerializer
from apps.consultations.api.serializers.appointment_request_serializers import (
    AppointmentRequestListSerializer,
    AppointmentRequestApprovePayloadSerializer,
    AppointmentRequestRejectPayloadSerializer,
    AppointmentRequestLinkPatientPayloadSerializer,
    AppointmentRequestConvertPayloadSerializer,
    AppointmentRequestBulkApprovePayloadSerializer,
    AppointmentRequestBulkRejectPayloadSerializer,
    AppointmentRequestExportPayloadSerializer,
    AppointmentRequestDetailSerializer,
    AppointmentRequestTimelineSerializer,
    AppointmentRequestActivityLogSerializer
)
from apps.consultations.services.appointment_request_service import AppointmentRequestService
from apps.consultations.services.pdf_service import PDFGenerationService
from apps.consultations.services.export_service import ExportService
from apps.consultations.choices import (
    AppointmentRequestStatus,
    AppointmentType,
    BookingSource,
    RelationshipToChild,
    Gender,
    AppointmentRequestTimelineEvent
)

class AppointmentRequestStatisticsAPIView(APIView):
    """
    GET /api/v1/appointment-requests/statistics/
    Retrieves aggregated dashboard statistics for appointment requests.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request):
        try:
            stats = AppointmentRequestService.get_statistics()
            return success_response(
                message="Statistics retrieved successfully.",
                data=stats
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred while retrieving statistics.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestListCreateAPIView(APIView):
    """
    GET /api/v1/appointment-requests/ -> Admin listing
    POST /api/v1/appointment-requests/ -> Public creation
    """
    def get_permissions(self):
        if self.request.method == 'POST':
            return [AllowAny()]
        return [IsAuthenticated(), IsAdminOrReceptionist()]

    def get(self, request):
        try:
            queryset = AppointmentRequestService.list_appointment_requests(request.query_params)
            
            # Reusable pagination
            paginator = StandardResultsSetPagination()
            page = paginator.paginate_queryset(queryset, request, view=self)
            
            serializer = AppointmentRequestListSerializer(page, many=True)
            paginated_data = {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data
            }
            return success_response(
                message="Appointment requests retrieved successfully.",
                data=paginated_data
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred while listing appointment requests.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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
                errors=e.detail if hasattr(e, 'detail') else (e.message_dict if hasattr(e, 'message_dict') else e.messages),
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return error_response(
                message="An unexpected error occurred while submitting the request.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestApproveAPIView(APIView):
    """
    POST /api/v1/appointment-requests/{id}/approve/
    Approves a request, updating reviewed_by, reviewed_at and status.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, id):
        serializer = AppointmentRequestApprovePayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        try:
            request_obj = AppointmentRequestService.approve_request(
                user=request.user,
                ip_address=ip_address,
                request_id=id,
                notes=serializer.validated_data.get("notes", "")
            )
            # Retrieve request details representation using AppointmentRequestDetailSerializer
            refetched_obj = AppointmentRequest.objects.select_related(
                'patient', 'reviewed_by', 'patient_linked_by', 'patient_created_by', 'patient__assigned_doctor'
            ).prefetch_related(
                'appointments', 'appointments__doctor'
            ).filter(id=id).first()
            output_serializer = AppointmentRequestDetailSerializer(refetched_obj, context={"request": request})
            return success_response(
                message="Appointment request approved successfully.",
                data=output_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(
                message="Approval validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during approval.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestRejectAPIView(APIView):
    """
    POST /api/v1/appointment-requests/{id}/reject/
    Rejects a request with a mandatory reason.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, id):
        serializer = AppointmentRequestRejectPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        try:
            request_obj = AppointmentRequestService.reject_request(
                user=request.user,
                ip_address=ip_address,
                request_id=id,
                reason=serializer.validated_data["reason"]
            )
            refetched_obj = AppointmentRequest.objects.select_related(
                'patient', 'reviewed_by', 'patient_linked_by', 'patient_created_by', 'patient__assigned_doctor'
            ).prefetch_related(
                'appointments', 'appointments__doctor'
            ).filter(id=id).first()
            output_serializer = AppointmentRequestDetailSerializer(refetched_obj, context={"request": request})
            return success_response(
                message="Appointment request rejected successfully.",
                data=output_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(
                message="Rejection validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during rejection.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestLinkPatientAPIView(APIView):
    """
    POST /api/v1/appointment-requests/{id}/link-patient/
    Links an existing patient to this appointment request.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, id):
        serializer = AppointmentRequestLinkPatientPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        try:
            request_obj = AppointmentRequestService.link_patient(
                user=request.user,
                ip_address=ip_address,
                request_id=id,
                patient_id=serializer.validated_data["patient_id"]
            )
            refetched_obj = AppointmentRequest.objects.select_related(
                'patient', 'reviewed_by', 'patient_linked_by', 'patient_created_by', 'patient__assigned_doctor'
            ).prefetch_related(
                'appointments', 'appointments__doctor'
            ).filter(id=id).first()
            output_serializer = AppointmentRequestDetailSerializer(refetched_obj, context={"request": request})
            return success_response(
                message="Patient linked successfully.",
                data=output_serializer.data,
                status_code=status.HTTP_200_OK
            )
        except ValidationError as e:
            return error_response(
                message="Linking validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during linking.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestCreatePatientAPIView(APIView):
    """
    POST /api/v1/appointment-requests/{id}/create-patient/
    Creates a new Patient record from the request details and links it.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, id):
        ip_address = get_client_ip(request)
        try:
            patient = AppointmentRequestService.create_patient(
                user=request.user,
                ip_address=ip_address,
                request_id=id
            )
            refetched_obj = AppointmentRequest.objects.select_related(
                'patient', 'reviewed_by', 'patient_linked_by', 'patient_created_by', 'patient__assigned_doctor'
            ).prefetch_related(
                'appointments', 'appointments__doctor'
            ).filter(id=id).first()
            output_serializer = AppointmentRequestDetailSerializer(refetched_obj, context={"request": request})
            return success_response(
                message="Patient created and linked successfully.",
                data=output_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return error_response(
                message="Patient creation validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during patient creation.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestConvertAPIView(APIView):
    """
    POST /api/v1/appointment-requests/{id}/convert/
    Converts an APPROVED request to a confirmed Appointment.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, id):
        serializer = AppointmentRequestConvertPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        try:
            appointment = AppointmentRequestService.convert_to_appointment(
                user=request.user,
                ip_address=ip_address,
                request_id=id,
                doctor_id=serializer.validated_data["doctor"],
                appointment_date=serializer.validated_data["appointment_date"],
                start_time=serializer.validated_data["start_time"],
                end_time=serializer.validated_data["end_time"]
            )
            refetched_obj = AppointmentRequest.objects.select_related(
                'patient', 'reviewed_by', 'patient_linked_by', 'patient_created_by', 'patient__assigned_doctor'
            ).prefetch_related(
                'appointments', 'appointments__doctor'
            ).filter(id=id).first()
            output_serializer = AppointmentRequestDetailSerializer(refetched_obj, context={"request": request})
            return success_response(
                message="Appointment created successfully from request.",
                data=output_serializer.data,
                status_code=status.HTTP_201_CREATED
            )
        except ValidationError as e:
            return error_response(
                message="Conversion validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during appointment conversion.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestSummaryAPIView(APIView):
    """
    GET /api/v1/appointment-requests/{id}/summary/
    Generates and downloads a summary PDF for this request.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request, id):
        request_obj = AppointmentRequest.objects.filter(id=id).first()
        if not request_obj:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        try:
            pdf_bytes = PDFGenerationService.generate_request_summary(request_obj)
            
            # Record print/summary timeline event
            AppointmentRequestService.log_timeline(
                appointment_request=request_obj,
                event_code=AppointmentRequestTimelineEvent.SUMMARY_PRINTED,
                title="Summary Printed",
                description=f"Summary PDF for request {request_obj.request_number} was printed by {request.user.email}.",
                performed_by=request.user,
                icon="print",
                color="orange"
            )

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="summary_{request_obj.request_number}.pdf"'
            return response
        except Exception as e:
            return error_response(
                message="Failed to generate PDF summary.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestFilterOptionsAPIView(APIView):
    """
    GET /api/v1/appointment-requests/filter-options/
    Returns filter metadata options for the listing UI.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request):
        try:
            # Query all active doctors
            doctors = User.objects.filter(user_roles__role__name='DOCTOR', is_active=True).values('id', 'first_name', 'last_name', 'email')
            doctors_list = [
                {
                    "id": str(doc["id"]),
                    "name": f"Dr. {doc['first_name']} {doc['last_name']}".strip() or doc["email"]
                }
                for doc in doctors
            ]

            # Query all users who have reviewed any request
            reviewer_ids = AppointmentRequest.objects.filter(reviewed_by__isnull=False).values_list('reviewed_by_id', flat=True).distinct()
            reviewers = User.objects.filter(id__in=reviewer_ids).values('id', 'first_name', 'last_name', 'email')
            reviewers_list = [
                {
                    "id": str(rev["id"]),
                    "name": f"{rev['first_name']} {rev['last_name']}".strip() or rev["email"]
                }
                for rev in reviewers
            ]

            filter_metadata = {
                "statuses": [{"value": choice[0], "label": choice[1]} for choice in AppointmentRequestStatus.choices],
                "doctors": doctors_list,
                "appointment_types": [{"value": choice[0], "label": choice[1]} for choice in AppointmentType.choices],
                "booking_sources": [{"value": choice[0], "label": choice[1]} for choice in BookingSource.choices],
                "reviewed_users": reviewers_list,
                "relationship_types": [{"value": choice[0], "label": choice[1]} for choice in RelationshipToChild.choices],
                "genders": [{"value": choice[0], "label": choice[1]} for choice in Gender.choices],
                "date_range_options": [
                    {"value": "today", "label": "Today"},
                    {"value": "yesterday", "label": "Yesterday"},
                    {"value": "last_7_days", "label": "Last 7 Days"},
                    {"value": "last_30_days", "label": "Last 30 Days"},
                    {"value": "custom", "label": "Custom Date Range"}
                ]
            }

            return success_response(
                message="Filter metadata retrieved successfully.",
                data=filter_metadata
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred while retrieving filter options.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestBulkApproveAPIView(APIView):
    """
    POST /api/v1/appointment-requests/bulk-approve/
    Approves multiple appointment requests in a batch.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request):
        serializer = AppointmentRequestBulkApprovePayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        try:
            result = AppointmentRequestService.bulk_approve(
                user=request.user,
                ip_address=ip_address,
                ids=serializer.validated_data["ids"]
            )
            return success_response(
                message="Bulk approval action executed.",
                data=result
            )
        except ValidationError as e:
            return error_response(
                message="Bulk approval validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during bulk approval.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestBulkRejectAPIView(APIView):
    """
    POST /api/v1/appointment-requests/bulk-reject/
    Rejects multiple appointment requests in a batch.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request):
        serializer = AppointmentRequestBulkRejectPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        ip_address = get_client_ip(request)
        try:
            result = AppointmentRequestService.bulk_reject(
                user=request.user,
                ip_address=ip_address,
                ids=serializer.validated_data["ids"],
                reason=serializer.validated_data["reason"]
            )
            return success_response(
                message="Bulk rejection action executed.",
                data=result
            )
        except ValidationError as e:
            return error_response(
                message="Bulk rejection validation failed.",
                errors=e.detail,
                status_code=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return error_response(
                message="An unexpected error occurred during bulk rejection.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestExportAPIView(APIView):
    """
    POST /api/v1/appointment-requests/export/
    Exports filtered appointment requests to CSV, Excel, or PDF.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request):
        serializer = AppointmentRequestExportPayloadSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response(
                message="Validation failed.",
                errors=serializer.errors,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        fmt = serializer.validated_data["format"]
        try:
            queryset = AppointmentRequestService.list_appointment_requests(serializer.validated_data)
            
            # Log export event for each exported request
            from apps.consultations.choices import AppointmentRequestTimelineEvent
            for request_obj in queryset:
                AppointmentRequestService.log_timeline(
                    appointment_request=request_obj,
                    event_code=AppointmentRequestTimelineEvent.EXPORTED,
                    title="Exported",
                    description=f"Request data was exported in {fmt} format by {request.user.email}.",
                    performed_by=request.user,
                    icon="download",
                    color="blue",
                    metadata={"format": fmt}
                )

            if fmt == 'CSV':
                csv_bytes = ExportService.export_csv(queryset)
                response = HttpResponse(csv_bytes, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="appointment_requests.csv"'
                return response
            elif fmt == 'Excel':
                excel_bytes = ExportService.export_excel(queryset)
                response = HttpResponse(excel_bytes, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                response['Content-Disposition'] = 'attachment; filename="appointment_requests.xlsx"'
                return response
            elif fmt == 'PDF':
                pdf_bytes = ExportService.export_pdf(queryset)
                response = HttpResponse(pdf_bytes, content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="appointment_requests.pdf"'
                return response
        except Exception as e:
            return error_response(
                message="Failed to export appointment requests.",
                errors={"non_field_errors": [str(e)]},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from apps.consultations.models import AppointmentRequestTimeline, AppointmentRequestActivityLog

class AppointmentRequestViewAPIView(APIView):
    """
    POST /api/v1/appointment-requests/{id}/view/
    Registers a viewed event, deduplicated within 5 minutes.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def post(self, request, id):
        request_obj = AppointmentRequest.objects.filter(id=id).first()
        if not request_obj:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        ip_address = get_client_ip(request)
        AppointmentRequestService.log_view(
            user=request.user,
            ip_address=ip_address,
            request_obj=request_obj
        )

        refetched_obj = AppointmentRequest.objects.select_related(
            'patient', 'reviewed_by', 'patient_linked_by', 'patient_created_by', 'patient__assigned_doctor'
        ).prefetch_related(
            'appointments', 'appointments__doctor'
        ).filter(id=id).first()
        
        serializer = AppointmentRequestDetailSerializer(refetched_obj, context={"request": request})
        return success_response(
            message="Appointment request view logged.",
            data=serializer.data,
            status_code=status.HTTP_200_OK
        )


class AppointmentRequestTimelineAPIView(APIView):
    """
    GET /api/v1/appointment-requests/{id}/timeline/
    Returns a paginated list of timeline events for this request.
    Supports filtering by event_code.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request, id):
        request_obj = AppointmentRequest.objects.filter(id=id).first()
        if not request_obj:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        queryset = AppointmentRequestTimeline.objects.filter(appointment_request=request_obj)
        
        # Filtering
        event_code = request.query_params.get("event_code")
        if event_code:
            queryset = queryset.filter(event_code=event_code)

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering in ["created_at", "-created_at"]:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AppointmentRequestTimelineSerializer(page, many=True)

        paginated_data = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }
        return success_response(
            message="Timeline events retrieved successfully.",
            data=paginated_data
        )


class AppointmentRequestActivityLogAPIView(APIView):
    """
    GET /api/v1/appointment-requests/{id}/activity-log/
    Returns a paginated list of activity log entries for this request.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request, id):
        request_obj = AppointmentRequest.objects.filter(id=id).first()
        if not request_obj:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        queryset = AppointmentRequestActivityLog.objects.filter(appointment_request=request_obj)

        # Ordering
        ordering = request.query_params.get("ordering", "-created_at")
        if ordering in ["created_at", "-created_at"]:
            queryset = queryset.order_by(ordering)
        else:
            queryset = queryset.order_by("-created_at")

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = AppointmentRequestActivityLogSerializer(page, many=True)

        paginated_data = {
            "count": paginator.page.paginator.count,
            "next": paginator.get_next_link(),
            "previous": paginator.get_previous_link(),
            "results": serializer.data
        }
        return success_response(
            message="Activity logs retrieved successfully.",
            data=paginated_data
        )


class AppointmentRequestConversionAPIView(APIView):
    """
    GET /api/v1/appointment-requests/{id}/conversion/
    Returns conversion status and appointment details if converted.
    """
    permission_classes = [IsAuthenticated, IsAdminOrReceptionist]

    def get(self, request, id):
        request_obj = AppointmentRequest.objects.filter(id=id).first()
        if not request_obj:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        conversion_data = AppointmentRequestService.build_conversion_response(request_obj)
        return success_response(
            message="Conversion details retrieved successfully.",
            data=conversion_data
        )
