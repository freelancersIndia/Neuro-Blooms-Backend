from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment
from apps.consultations.choices import NoteVisibility

class AppointmentNote(BaseModel):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="notes",
        verbose_name="Appointment"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointment_notes",
        verbose_name="User"
    )
    note = models.TextField(verbose_name="Note")
    visibility = models.CharField(
        max_length=20,
        choices=NoteVisibility.choices,
        default=NoteVisibility.PRIVATE,
        verbose_name="Visibility"
    )

    class Meta:
        db_table = "consultations_appointment_notes"
        verbose_name = "Appointment Note"
        verbose_name_plural = "Appointment Notes"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Note by {self.user.email} on Appointment {self.appointment.appointment_number} ({self.visibility})"
