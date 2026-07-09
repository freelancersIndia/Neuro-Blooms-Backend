from django.urls import path
from apps.consultations.api.views.appointment_request import (
    AppointmentRequestStatisticsAPIView,
    AppointmentRequestListCreateAPIView,
    AppointmentRequestApproveAPIView,
    AppointmentRequestRejectAPIView,
    AppointmentRequestLinkPatientAPIView,
    AppointmentRequestCreatePatientAPIView,
    AppointmentRequestConvertAPIView,
    AppointmentRequestSummaryAPIView,
    AppointmentRequestFilterOptionsAPIView,
    AppointmentRequestBulkApproveAPIView,
    AppointmentRequestBulkRejectAPIView,
    AppointmentRequestExportAPIView,
    AppointmentRequestViewAPIView,
    AppointmentRequestTimelineAPIView,
    AppointmentRequestActivityLogAPIView,
    AppointmentRequestConversionAPIView
)
from apps.consultations.api.views.appointment_management import (
    AppointmentRequestDetailAPIView,
    AppointmentRequestRescheduleAPIView
)

urlpatterns = [
    # Statistics
    path('appointment-requests/statistics/', AppointmentRequestStatisticsAPIView.as_view(), name='appointment-request-statistics'),
    
    # Filter options
    path('appointment-requests/filter-options/', AppointmentRequestFilterOptionsAPIView.as_view(), name='appointment-request-filter-options'),
    
    # Bulk actions
    path('appointment-requests/bulk-approve/', AppointmentRequestBulkApproveAPIView.as_view(), name='appointment-request-bulk-approve'),
    path('appointment-requests/bulk-reject/', AppointmentRequestBulkRejectAPIView.as_view(), name='appointment-request-bulk-reject'),
    
    # Export
    path('appointment-requests/export/', AppointmentRequestExportAPIView.as_view(), name='appointment-request-export'),
    
    # Listing and creation
    path('appointment-requests/', AppointmentRequestListCreateAPIView.as_view(), name='appointment-request-list'),
    path('appointment-requests/', AppointmentRequestListCreateAPIView.as_view(), name='booking_appointment_request_create'),
    
    # Detail and action endpoints
    path('appointment-requests/<uuid:id>/', AppointmentRequestDetailAPIView.as_view(), name='appointment-request-detail'),
    path('appointment-requests/<uuid:id>/approve/', AppointmentRequestApproveAPIView.as_view(), name='appointment-request-approve'),
    path('appointment-requests/<uuid:id>/reject/', AppointmentRequestRejectAPIView.as_view(), name='appointment-request-reject'),
    path('appointment-requests/<uuid:id>/reschedule/', AppointmentRequestRescheduleAPIView.as_view(), name='appointment-request-reschedule'),
    path('appointment-requests/<uuid:id>/link-patient/', AppointmentRequestLinkPatientAPIView.as_view(), name='appointment-request-link-patient'),
    path('appointment-requests/<uuid:id>/create-patient/', AppointmentRequestCreatePatientAPIView.as_view(), name='appointment-request-create-patient'),
    path('appointment-requests/<uuid:id>/convert/', AppointmentRequestConvertAPIView.as_view(), name='appointment-request-convert'),
    path('appointment-requests/<uuid:id>/summary/', AppointmentRequestSummaryAPIView.as_view(), name='appointment-request-summary'),
    
    # New detail workflow endpoints
    path('appointment-requests/<uuid:id>/view/', AppointmentRequestViewAPIView.as_view(), name='appointment-request-view'),
    path('appointment-requests/<uuid:id>/timeline/', AppointmentRequestTimelineAPIView.as_view(), name='appointment-request-timeline'),
    path('appointment-requests/<uuid:id>/activity-log/', AppointmentRequestActivityLogAPIView.as_view(), name='appointment-request-activity-log'),
    path('appointment-requests/<uuid:id>/conversion/', AppointmentRequestConversionAPIView.as_view(), name='appointment-request-conversion'),
]
