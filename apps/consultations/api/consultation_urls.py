from django.urls import path
from apps.consultations.api.views.consultation import (
    ConsultationAppointmentDetailAPIView,
    PatientSummaryAPIView,
    PreviousConsultationsAPIView,
    FollowupHistoryAPIView,
    ConsultationCreateAPIView,
    ConsultationUpdateAPIView,
    ConsultationAttachmentListUploadAPIView,
    ConsultationAttachmentDeleteAPIView,
    ConsultationCompleteAPIView
)

urlpatterns = [
    path('appointments/<uuid:appointment_id>/', ConsultationAppointmentDetailAPIView.as_view(), name='consultation-appointment-detail'),
    path('patient-summary/<uuid:patient_id>/', PatientSummaryAPIView.as_view(), name='consultation-patient-summary'),
    path('history/<uuid:patient_id>/', PreviousConsultationsAPIView.as_view(), name='consultation-history'),
    path('followups/<uuid:patient_id>/', FollowupHistoryAPIView.as_view(), name='consultation-followup-history'),
    path('', ConsultationCreateAPIView.as_view(), name='consultation-create'),
    path('<uuid:consultation_id>/', ConsultationUpdateAPIView.as_view(), name='consultation-update'),
    path('<uuid:consultation_id>/attachments/', ConsultationAttachmentListUploadAPIView.as_view(), name='consultation-attachment-list-upload'),
    path('<uuid:consultation_id>/attachments/<uuid:attachment_id>/', ConsultationAttachmentDeleteAPIView.as_view(), name='consultation-attachment-delete'),
    path('<uuid:consultation_id>/complete/', ConsultationCompleteAPIView.as_view(), name='consultation-complete'),
]
