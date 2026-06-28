from django.urls import path
from apps.consultations.api.views.appointment import (
    AvailableSlotsAPIView,
    ValidateSlotAPIView
)
from apps.consultations.api.views.appointment_management import (
    AppointmentListAPIView,
    AppointmentDetailAPIView,
    AppointmentRescheduleAPIView,
    AppointmentCancelAPIView,
    AppointmentCheckInAPIView,
    AppointmentStartConsultationAPIView,
    AppointmentMarkNoShowAPIView
)

urlpatterns = [
    path('available-slots/', AvailableSlotsAPIView.as_view(), name='available-slots'),
    path('validate-slot/', ValidateSlotAPIView.as_view(), name='validate-slot'),
    path('', AppointmentListAPIView.as_view(), name='appointment-booking'),
    path('<uuid:id>/', AppointmentDetailAPIView.as_view(), name='appointment-detail'),
    path('<uuid:id>/reschedule/', AppointmentRescheduleAPIView.as_view(), name='appointment-reschedule'),
    path('<uuid:id>/cancel/', AppointmentCancelAPIView.as_view(), name='appointment-cancel'),
    path('<uuid:id>/check-in/', AppointmentCheckInAPIView.as_view(), name='appointment-check-in'),
    path('<uuid:id>/start-consultation/', AppointmentStartConsultationAPIView.as_view(), name='appointment-start-consultation'),
    path('<uuid:id>/mark-no-show/', AppointmentMarkNoShowAPIView.as_view(), name='appointment-mark-no-show'),
]
