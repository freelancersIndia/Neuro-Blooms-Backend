from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment

class AppointmentTimeline(BaseModel):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="timeline_events",
        verbose_name="Appointment"
    )
    event = models.CharField(max_length=100, verbose_name="Event")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_timeline_events",
        verbose_name="Performed By"
    )

    class Meta:
        db_table = "consultations_appointment_timelines"
        verbose_name = "Appointment Timeline"
        verbose_name_plural = "Appointment Timelines"
        ordering = ["created_at"]

    def __str__(self):
        performed_str = f" by {self.performed_by.email}" if self.performed_by else ""
        return f"Appt {self.appointment.appointment_number}: {self.event}{performed_str} at {self.created_at}"
