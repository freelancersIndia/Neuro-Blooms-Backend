from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.patient import Patient

class PatientTimeline(BaseModel):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="timeline_events",
        verbose_name="Patient"
    )
    event = models.CharField(max_length=100, verbose_name="Event")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="patient_timeline_events",
        verbose_name="Performed By"
    )

    class Meta:
        db_table = "consultations_patient_timelines"
        verbose_name = "Patient Timeline"
        verbose_name_plural = "Patient Timelines"
        ordering = ["created_at"]

    def __str__(self):
        performed_str = f" by {self.performed_by.email}" if self.performed_by else ""
        return f"Patient {self.patient.patient_number}: {self.event}{performed_str} at {self.created_at}"
