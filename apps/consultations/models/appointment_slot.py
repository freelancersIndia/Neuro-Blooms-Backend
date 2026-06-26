from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment
from apps.consultations.choices import SlotStatus

class AppointmentSlot(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointment_slots",
        verbose_name="Doctor"
    )
    slot_date = models.DateField(verbose_name="Slot Date")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    status = models.CharField(
        max_length=20,
        choices=SlotStatus.choices,
        default=SlotStatus.AVAILABLE,
        verbose_name="Status"
    )
    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointment_slots",
        verbose_name="Appointment"
    )

    class Meta:
        db_table = "consultations_appointment_slots"
        verbose_name = "Appointment Slot"
        verbose_name_plural = "Appointment Slots"
        ordering = ["slot_date", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "slot_date", "start_time", "end_time"],
                name="unique_doctor_slot"
            )
        ]
        indexes = [
            models.Index(fields=["doctor"], name="idx_slot_doctor"),
            models.Index(fields=["slot_date"], name="idx_slot_date"),
            models.Index(fields=["status"], name="idx_slot_status"),
        ]

    def __str__(self):
        return f"Slot for Dr. {self.doctor.email} on {self.slot_date} ({self.start_time} - {self.end_time}) - {self.status}"
