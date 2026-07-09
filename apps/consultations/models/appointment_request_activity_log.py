from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment_request import AppointmentRequest

class AppointmentRequestActivityLog(BaseModel):
    appointment_request = models.ForeignKey(
        AppointmentRequest,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        verbose_name="Appointment Request"
    )
    action = models.CharField(max_length=50, verbose_name="Action")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_request_activity_logs",
        verbose_name="Performed By"
    )
    old_values = models.JSONField(null=True, blank=True, verbose_name="Old Values")
    new_values = models.JSONField(null=True, blank=True, verbose_name="New Values")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")
    browser = models.CharField(max_length=255, blank=True, null=True, verbose_name="Browser")
    user_agent = models.CharField(max_length=500, blank=True, null=True, verbose_name="User Agent")
    booking_source = models.CharField(max_length=50, blank=True, null=True, verbose_name="Booking Source")

    class Meta:
        db_table = "consultations_appointment_request_activity_logs"
        verbose_name = "Appointment Request Activity Log"
        verbose_name_plural = "Appointment Request Activity Logs"
        ordering = ["-created_at"]

    def __str__(self):
        performed_str = f" by {self.performed_by.email}" if self.performed_by else "Anonymous"
        return f"Request {self.appointment_request.request_number}: {self.action}{performed_str} at {self.created_at}"
