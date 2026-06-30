from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.consultations.api.booking_urls')),
    path('api/v1/', include('apps.accounts.api.urls')),
    path('api/v1/admin/', include('apps.consultations.api.urls')),
    path('api/v1/public/', include('apps.consultations.api.public_urls')),
    path('api/v1/appointments/', include('apps.consultations.api.appointment_urls')),
    path('api/v1/', include('apps.consultations.api.patient_matching_urls')),
    path('api/v1/consultations/', include('apps.consultations.api.consultation_urls')),
    path('api/v1/', include('apps.consultations.api.followup_urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

