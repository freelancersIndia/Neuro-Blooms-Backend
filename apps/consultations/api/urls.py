from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.consultations.api.views import (
    PublicConsultationRequestAPIView,
    AppointmentRequestListAPIView,
    AppointmentRequestDetailAPIView,
    AppointmentRequestStatisticsAPIView,
    AppointmentRequestApproveAPIView,
    AppointmentRequestRejectAPIView,
    AppointmentRequestTimelineAPIView,
    AppointmentRequestExportAPIView,
    PatientMatchingAPIView,
    PatientSearchAPIView,
    PatientLinkAPIView,
    PatientCreateAPIView,
    PatientPreviewAPIView,
    PatientViewSet,
)

router = DefaultRouter()
router.register('patients', PatientViewSet, basename='patients')

urlpatterns = [
    path('public/consultation-request/', PublicConsultationRequestAPIView.as_view(), name='public_consultation_request'),
    path('appointments/requests/', AppointmentRequestListAPIView.as_view(), name='appointment_request_list'),
    path('appointments/requests/statistics/', AppointmentRequestStatisticsAPIView.as_view(), name='appointment_request_statistics'),
    path('appointments/requests/export/', AppointmentRequestExportAPIView.as_view(), name='appointment_request_export'),
    path('appointments/requests/<uuid:id>/', AppointmentRequestDetailAPIView.as_view(), name='appointment_request_detail'),
    path('appointments/requests/<uuid:id>/approve/', AppointmentRequestApproveAPIView.as_view(), name='appointment_request_approve'),
    path('appointments/requests/<uuid:id>/reject/', AppointmentRequestRejectAPIView.as_view(), name='appointment_request_reject'),
    path('appointments/requests/<uuid:id>/timeline/', AppointmentRequestTimelineAPIView.as_view(), name='appointment_request_timeline'),
    
    # Patient Matching and Creation Module (Phase 3)
    path('patient-matching/<str:appointment_request_id>/', PatientMatchingAPIView.as_view(), name='patient_matching_screen'),
    path('patient-matching/<str:appointment_request_id>/link/', PatientLinkAPIView.as_view(), name='patient_matching_link'),
    path('patient-matching/<str:appointment_request_id>/create-patient/', PatientCreateAPIView.as_view(), name='patient_matching_create_patient'),
    path('patients/<str:patient_id>/preview/', PatientPreviewAPIView.as_view(), name='patient_preview'),
    
    # Include Router for Patient Management Module (Phase 4)
    path('', include(router.urls)),
]
