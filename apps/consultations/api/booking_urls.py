from django.urls import path
from apps.consultations.api.views.booking import (
    PublicDoctorListView,
    AvailableDatesView,
    AvailableSlotsView,
    AppointmentRequestCreateView
)

urlpatterns = [
    path('doctors/', PublicDoctorListView.as_view(), name='booking_doctor_list'),
    path('doctors/<uuid:doctor_id>/available-dates/', AvailableDatesView.as_view(), name='booking_available_dates'),
    path('doctors/<uuid:doctor_id>/available-slots/', AvailableSlotsView.as_view(), name='booking_available_slots'),
    path('appointment-requests/', AppointmentRequestCreateView.as_view(), name='booking_appointment_request_create'),
]
