from django.urls import path
from apps.consultations.api.views.public import (
    PublicDoctorListView,
    PublicAvailableSlotsView,
    PublicAppointmentRequestCreateView
)

urlpatterns = [
    path('doctors/', PublicDoctorListView.as_view(), name='public-doctor-list'),
    path('appointments/available-slots/', PublicAvailableSlotsView.as_view(), name='public-available-slots'),
    path('appointment-requests/', PublicAppointmentRequestCreateView.as_view(), name='public-appointment-request-create'),
]
