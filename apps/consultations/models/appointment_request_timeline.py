from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment_request import AppointmentRequest
from apps.consultations.choices import AppointmentRequestTimelineEvent

class AppointmentRequestTimeline(BaseModel):
    appointment_request = models.ForeignKey(
        AppointmentRequest,
        on_delete=models.CASCADE,
        related_name="timeline_events",
        verbose_name="Appointment Request"
    )
    event_code = models.CharField(
        max_length=50,
        choices=AppointmentRequestTimelineEvent.choices,
        verbose_name="Event Code"
    )
    title = models.CharField(max_length=150, verbose_name="Title")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_request_timeline_events",
        verbose_name="Performed By"
    )
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")
    icon = models.CharField(max_length=50, blank=True, null=True, verbose_name="Icon")
    color = models.CharField(max_length=30, blank=True, null=True, verbose_name="Color")

    class Meta:
        db_table = "consultations_appointment_request_timelines"
        verbose_name = "Appointment Request Timeline"
        verbose_name_plural = "Appointment Request Timelines"
        ordering = ["created_at"]

    def __str__(self):
        performed_str = f" by {self.performed_by.email}" if self.performed_by else ""
        return f"Request {self.appointment_request.request_number}: {self.event_code}{performed_str} at {self.created_at}"
