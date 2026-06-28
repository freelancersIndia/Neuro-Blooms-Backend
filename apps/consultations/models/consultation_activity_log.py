from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment
from apps.consultations.models.patient import Patient
from apps.consultations.models.consultation import Consultation

class ConsultationActivityLog(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultation_activity_logs",
        verbose_name="Doctor"
    )
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="consultation_activity_logs",
        verbose_name="Patient"
    )
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="activity_logs",
        verbose_name="Consultation"
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="consultation_activity_logs",
        verbose_name="Appointment"
    )
    action = models.CharField(max_length=50, verbose_name="Action")
    old_values = models.JSONField(null=True, blank=True, verbose_name="Old Values")
    new_values = models.JSONField(null=True, blank=True, verbose_name="New Values")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP Address")

    class Meta:
        db_table = "consultations_consultation_activity_logs"
        verbose_name = "Consultation Activity Log"
        verbose_name_plural = "Consultation Activity Logs"
        ordering = ["-created_at"]

    def __str__(self):
        doctor_email = self.doctor.email if self.doctor else "Anonymous"
        return f"{doctor_email} - {self.action} for Patient {self.patient.id} at {self.created_at}"
