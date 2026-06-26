from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment
from apps.consultations.choices import AppointmentStatus

class AppointmentStatusHistory(BaseModel):
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="status_history",
        verbose_name="Appointment"
    )
    previous_status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        blank=True,
        null=True,
        verbose_name="Previous Status"
    )
    new_status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        verbose_name="New Status"
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointment_status_changes",
        verbose_name="Changed By"
    )
    reason = models.TextField(blank=True, null=True, verbose_name="Reason")

    class Meta:
        db_table = "consultations_appointment_status_history"
        verbose_name = "Appointment Status History"
        verbose_name_plural = "Appointment Status Histories"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["appointment"], name="idx_appthist_appt"),
            models.Index(fields=["new_status"], name="idx_appthist_status"),
        ]

    def __str__(self):
        prev_str = self.previous_status if self.previous_status else "None"
        return f"Appt {self.appointment.appointment_number}: {prev_str} -> {self.new_status} by {self.changed_by.email}"
