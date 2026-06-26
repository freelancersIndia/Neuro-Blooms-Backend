import csv
import logging
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from apps.accounts.utils.ip import get_client_ip
from apps.accounts.utils.responses import success_response, error_response
from apps.accounts.models.activity_log import ActivityLog
from apps.consultations.models import AppointmentRequest
from apps.consultations.api.permissions import IsAdminOrReceptionist
from apps.consultations.api.serializers import (
    AppointmentRequestListSerializer,
    AppointmentRequestDetailSerializer,
    AppointmentRequestRejectSerializer,
)
from apps.consultations.services import AppointmentRequestService, ConflictException

logger = logging.getLogger(__name__)


class Echo:
    """
    An object that implements just the write method of the file-like interface.
    Used for streaming CSV generation.
    """
    def write(self, value):
        return value


def export_requests_csv(queryset):
    """
    Generates a StreamingHttpResponse containing requests details in CSV format.
    Ensures memory efficiency by chunking the database query via iterator().
    """
    pseudo_buffer = Echo()
    writer = csv.writer(pseudo_buffer)

    def csv_iterator():
        # Yield the header row
        yield writer.writerow([
            'Request Number', 'Parent', 'Child', 'Mobile',
            'Concern', 'Preferred Date', 'Status', 'Submitted Date'
        ])

        # Fetch records in chunks to optimize memory usage
        for req in queryset.select_related('reviewed_by').iterator(chunk_size=1000):
            parent_name = f"{req.parent_first_name} {req.parent_last_name}"
            child_name = f"{req.child_first_name} {req.child_last_name}"
            submitted_date = req.created_at.strftime('%Y-%m-%d %H:%M:%S') if req.created_at else "N/A"
            status_display = req.get_status_display()
            
            # Map concern to its human-readable choice display if matching key is found
            primary_concern_display = req.get_primary_concern_display() if hasattr(req, 'get_primary_concern_display') else req.primary_concern

            yield writer.writerow([
                req.request_number,
                parent_name,
                child_name,
                req.mobile_number,
                primary_concern_display,
                str(req.preferred_date),
                status_display,
                submitted_date
            ])

    response = StreamingHttpResponse(csv_iterator(), content_type="text/csv")
    response['Content-Disposition'] = 'attachment; filename="appointment_requests.csv"'
    return response


class AppointmentRequestPagination(PageNumberPagination):
    """
    Custom pagination configuration enforcing the required list structure:
    - statistics
    - results
    - pagination metadata
    """
    page_size = 10
    max_page_size = 100
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        view = self.request.parser_context.get('view') if self.request else None
        stats = getattr(view, 'statistics_data', {})
        total_pages = self.page.paginator.num_pages if self.page else 0
        current_page = self.page.number if self.page else 1
        page_size = self.get_page_size(self.request)

        return success_response(
            message="Appointment requests fetched successfully.",
            data={
                "statistics": stats,
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


class AppointmentRequestListAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]
    pagination_class = AppointmentRequestPagination

    def get(self, request):
        """
        Retrieves paginated, filtered, searched and sorted appointment requests.
        Enforces IsAdminOrReceptionist permission check.
        """
        queryset = AppointmentRequestService.get_filtered_requests(request.query_params)
        
        # Access statistics to merge in paginated envelope
        self.statistics_data = AppointmentRequestService.get_statistics()
        logger.info(f"User {request.user.email} listed appointment requests.")

        paginator = self.pagination_class()
        try:
            page = paginator.paginate_queryset(queryset, request, view=self)
            if page is not None:
                serializer = AppointmentRequestListSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)
        except Exception as e:
            logger.warning(f"Pagination error: {str(e)}")
            return error_response(
                message=str(e),
                errors=None,
                status_code=status.HTTP_400_BAD_REQUEST
            )

        serializer = AppointmentRequestListSerializer(queryset, many=True)
        return success_response(
            message="Appointment requests fetched successfully.",
            data={
                "statistics": self.statistics_data,
                "results": serializer.data,
                "pagination": None
            }
        )


class AppointmentRequestDetailAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]

    def get(self, request, id):
        """
        Fetches single appointment request details.
        Logs APPOINTMENT_REQUEST_VIEWED activity on each access.
        """
        try:
            appt_request = AppointmentRequest.objects.get(id=id)
        except AppointmentRequest.DoesNotExist:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )

        # Log viewing action in ActivityLog
        try:
            ActivityLog.objects.create(
                user=request.user,
                action='APPOINTMENT_REQUEST_VIEWED',
                description=f"Appointment request viewed. Request Number: {appt_request.request_number}",
                ip_address=get_client_ip(request)
            )
        except Exception as log_err:
            logger.error(f"Failed to log viewing activity for request {appt_request.request_number}: {str(log_err)}")

        logger.info(f"User {request.user.email} viewed details of request {appt_request.request_number}.")
        
        serializer = AppointmentRequestDetailSerializer(appt_request)
        return success_response(
            message="Appointment request details retrieved successfully.",
            data=serializer.data
        )


class AppointmentRequestStatisticsAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]

    def get(self, request):
        """
        Returns aggregated counters (total, pending, approved, rejected).
        """
        logger.info(f"User {request.user.email} accessed requests statistics dashboard.")
        stats = AppointmentRequestService.get_statistics()
        return success_response(
            message="Appointment request statistics retrieved successfully.",
            data=stats
        )


class AppointmentRequestApproveAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]

    def post(self, request, id):
        """
        Approves a pending request. Returns conflict response if not PENDING.
        """
        try:
            AppointmentRequestService.approve_request(
                request_id=id,
                user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="Appointment request approved successfully."
            )
        except AppointmentRequest.DoesNotExist:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ConflictException as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Approval error for request {id}: {str(e)}", exc_info=True)
            return error_response(
                message="An error occurred during request approval.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestRejectAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]

    def post(self, request, id):
        """
        Rejects a pending request. Requires rejection reason.
        """
        serializer = AppointmentRequestRejectSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except Exception as err:
            logger.warning(f"Rejection input validation failed: {getattr(err, 'detail', str(err))}")
            raise err

        reason = serializer.validated_data['reason']

        try:
            AppointmentRequestService.reject_request(
                request_id=id,
                reason=reason,
                user=request.user,
                ip_address=get_client_ip(request)
            )
            return success_response(
                message="Appointment request rejected successfully."
            )
        except AppointmentRequest.DoesNotExist:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )
        except ConflictException as e:
            return Response({
                "success": False,
                "message": str(e)
            }, status=status.HTTP_409_CONFLICT)
        except Exception as e:
            logger.error(f"Rejection error for request {id}: {str(e)}", exc_info=True)
            return error_response(
                message="An error occurred during request rejection.",
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AppointmentRequestTimelineAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]

    def get(self, request, id):
        """
        Retrieves request lifecycle event history.
        """
        logger.info(f"User {request.user.email} viewed timeline for request {id}.")
        try:
            timeline = AppointmentRequestService.get_timeline(id)
            return success_response(
                message="Request timeline retrieved successfully.",
                data=timeline
            )
        except AppointmentRequest.DoesNotExist:
            return error_response(
                message="Appointment request not found.",
                status_code=status.HTTP_404_NOT_FOUND
            )


class AppointmentRequestExportAPIView(APIView):
    permission_classes = [IsAdminOrReceptionist]

    def get(self, request):
        """
        Triggers stream download of CSV representation of requests.
        """
        logger.info(f"User {request.user.email} triggered requests list export.")
        queryset = AppointmentRequestService.get_filtered_requests(request.query_params)
        return export_requests_csv(queryset)
