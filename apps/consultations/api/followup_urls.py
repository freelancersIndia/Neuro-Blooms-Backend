from django.urls import path
from apps.consultations.api.views.followup import (
    FollowupDecisionAPIView,
    FollowupCreateAPIView,
    FollowupDetailAPIView,
    PatientFollowupsListAPIView,
    FollowupCancelAPIView,
    TreatmentCaseDetailAPIView,
    TreatmentCaseCloseAPIView,
    TreatmentCaseReopenAPIView
)

urlpatterns = [
    path('consultations/<uuid:consultation_id>/follow-up-decision/', FollowupDecisionAPIView.as_view(), name='consultation-followup-decision'),
    path('followups/', FollowupCreateAPIView.as_view(), name='followup-create'),
    path('followups/<uuid:appointment_id>/', FollowupDetailAPIView.as_view(), name='followup-detail'),
    path('patients/<uuid:patient_id>/followups/', PatientFollowupsListAPIView.as_view(), name='patient-followups-list'),
    path('followups/<uuid:appointment_id>/cancel/', FollowupCancelAPIView.as_view(), name='followup-cancel'),
    path('treatment-cases/<uuid:patient_id>/', TreatmentCaseDetailAPIView.as_view(), name='treatment-case-detail'),
    path('treatment-cases/<uuid:patient_id>/close/', TreatmentCaseCloseAPIView.as_view(), name='treatment-case-close'),
    path('treatment-cases/<uuid:patient_id>/reopen/', TreatmentCaseReopenAPIView.as_view(), name='treatment-case-reopen'),
]
