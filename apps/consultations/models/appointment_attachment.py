from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment

class AppointmentAttachment(BaseModel):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Appointment"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_attachments",
        verbose_name="Uploaded By"
    )
    file = models.FileField(upload_to="appointment_attachments/", verbose_name="Attachment File")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        db_table = "consultations_appointment_attachments"
        verbose_name = "Appointment Attachment"
        verbose_name_plural = "Appointment Attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Attachment for Appt {self.appointment.appointment_number} by {self.uploaded_by.email}"
