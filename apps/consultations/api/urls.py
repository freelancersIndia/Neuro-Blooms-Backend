from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.consultations.api.views.clinic_settings import ClinicSettingsAPIView
from apps.consultations.api.views.weekly_schedule import WeeklyScheduleAPIView
from apps.consultations.api.views.clinic_holiday import ClinicHolidayViewSet
from apps.consultations.api.views.clinic_break import ClinicBreakViewSet

router = DefaultRouter()
router.register(r'clinic/holidays', ClinicHolidayViewSet, basename='clinic-holiday')
router.register(r'clinic/breaks', ClinicBreakViewSet, basename='clinic-break')

urlpatterns = [
    path('clinic/settings/', ClinicSettingsAPIView.as_view(), name='clinic-settings'),
    path('clinic/weekly-schedule/', WeeklyScheduleAPIView.as_view(), name='clinic-weekly-schedule'),
    path('', include(router.urls)),
]
