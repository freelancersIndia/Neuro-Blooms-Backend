from django.urls import path
from apps.consultations.api.views import (
    PublicConsultationRequestAPIView,
    AppointmentRequestListAPIView,
    AppointmentRequestDetailAPIView,
    AppointmentRequestStatisticsAPIView,
    AppointmentRequestApproveAPIView,
    AppointmentRequestRejectAPIView,
    AppointmentRequestTimelineAPIView,
    AppointmentRequestExportAPIView,
)

urlpatterns = [
    path('public/consultation-request/', PublicConsultationRequestAPIView.as_view(), name='public_consultation_request'),
    path('appointments/requests/', AppointmentRequestListAPIView.as_view(), name='appointment_request_list'),
    path('appointments/requests/statistics/', AppointmentRequestStatisticsAPIView.as_view(), name='appointment_request_statistics'),
    path('appointments/requests/export/', AppointmentRequestExportAPIView.as_view(), name='appointment_request_export'),
    path('appointments/requests/<uuid:id>/', AppointmentRequestDetailAPIView.as_view(), name='appointment_request_detail'),
    path('appointments/requests/<uuid:id>/approve/', AppointmentRequestApproveAPIView.as_view(), name='appointment_request_approve'),
    path('appointments/requests/<uuid:id>/reject/', AppointmentRequestRejectAPIView.as_view(), name='appointment_request_reject'),
    path('appointments/requests/<uuid:id>/timeline/', AppointmentRequestTimelineAPIView.as_view(), name='appointment_request_timeline'),
]
