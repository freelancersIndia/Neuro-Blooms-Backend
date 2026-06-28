from django.urls import path
from apps.consultations.api.views.patient_matching import (
    PatientMatchingAPIView,
    PatientMatchDetailsAPIView,
    PatientLinkAPIView,
    PatientCreateAPIView,
    PatientMatchingStatisticsAPIView,
    PatientSearchAPIView
)
from apps.consultations.api.views.appointment_management import (
    AppointmentRequestDetailAPIView,
    AppointmentRequestApproveAPIView,
    AppointmentRequestRejectAPIView,
    AppointmentRequestRescheduleAPIView
)

urlpatterns = [
    path('patient-matching/', PatientMatchingAPIView.as_view(), name='patient-matching'),
    path('patient-matching/<uuid:patient_id>/details/', PatientMatchDetailsAPIView.as_view(), name='patient-match-details'),
    path('patient-matching/link/', PatientLinkAPIView.as_view(), name='patient-link'),
    path('patient-matching/create-patient/', PatientCreateAPIView.as_view(), name='patient-create-patient'),
    path('patient-matching/statistics/', PatientMatchingStatisticsAPIView.as_view(), name='patient-matching-statistics'),
    path('patients/search/', PatientSearchAPIView.as_view(), name='patient-search'),
    
    path('appointment-requests/<uuid:id>/', AppointmentRequestDetailAPIView.as_view(), name='appointment-request-detail'),
    path('appointment-requests/<uuid:id>/approve/', AppointmentRequestApproveAPIView.as_view(), name='appointment-request-approve'),
    path('appointment-requests/<uuid:id>/reject/', AppointmentRequestRejectAPIView.as_view(), name='appointment-request-reject'),
    path('appointment-requests/<uuid:id>/reschedule/', AppointmentRequestRescheduleAPIView.as_view(), name='appointment-request-reschedule'),
]
