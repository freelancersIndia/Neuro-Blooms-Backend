from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.consultations.api.views.clinic_settings import ClinicSettingsAPIView
from apps.consultations.api.views.weekly_schedule import WeeklyScheduleAPIView
from apps.consultations.api.views.clinic_holiday import ClinicHolidayViewSet
from apps.consultations.api.views.clinic_break import ClinicBreakViewSet
from apps.consultations.api.views.doctor_availability import DoctorAvailabilityAPIView
from apps.consultations.api.views.doctor_working_day import DoctorWorkingDayAPIView
from apps.consultations.api.views.doctor_leave import DoctorLeaveViewSet
from apps.consultations.api.views.doctor_blocked_slot import DoctorBlockedSlotViewSet

router = DefaultRouter()
router.register(r'clinic/holidays', ClinicHolidayViewSet, basename='clinic-holiday')
router.register(r'clinic/breaks', ClinicBreakViewSet, basename='clinic-break')

urlpatterns = [
    path('clinic/settings/', ClinicSettingsAPIView.as_view(), name='clinic-settings'),
    path('clinic/weekly-schedule/', WeeklyScheduleAPIView.as_view(), name='clinic-weekly-schedule'),

    # Doctor Availability
    path('doctors/<uuid:doctor_id>/availability/', DoctorAvailabilityAPIView.as_view(), name='doctor-availability'),

    # Doctor Working Days
    path('doctors/<uuid:doctor_id>/working-days/', DoctorWorkingDayAPIView.as_view(), name='doctor-working-days'),

    # Doctor Leaves
    path('doctors/<uuid:doctor_id>/leaves/', DoctorLeaveViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='doctor-leave-list'),
    path('doctors/<uuid:doctor_id>/leaves/<uuid:pk>/', DoctorLeaveViewSet.as_view({
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='doctor-leave-detail'),

    # Doctor Blocked Slots
    path('doctors/<uuid:doctor_id>/blocked-slots/', DoctorBlockedSlotViewSet.as_view({
        'get': 'list',
        'post': 'create'
    }), name='doctor-blocked-slot-list'),
    path('doctors/<uuid:doctor_id>/blocked-slots/<uuid:pk>/', DoctorBlockedSlotViewSet.as_view({
        'patch': 'partial_update',
        'delete': 'destroy'
    }), name='doctor-blocked-slot-detail'),

    path('', include(router.urls)),
]
