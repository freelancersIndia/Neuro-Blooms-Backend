from django.db import models
from apps.consultations.models.base import BaseModel

class AppointmentSettings(BaseModel):
    slot_duration = models.PositiveIntegerField(default=30, verbose_name="Slot Duration (Minutes)")
    clinic_start_time = models.TimeField(verbose_name="Clinic Start Time")
    clinic_end_time = models.TimeField(verbose_name="Clinic End Time")
    max_bookings_per_slot = models.PositiveIntegerField(default=1, verbose_name="Max Bookings Per Slot")
    buffer_minutes = models.PositiveIntegerField(default=5, verbose_name="Buffer Minutes")

    class Meta:
        db_table = "consultations_appointment_settings"
        verbose_name = "Appointment Settings"
        verbose_name_plural = "Appointment Settings"
        ordering = ["created_at"]

    def __str__(self):
        return f"Global Appointment Settings (Slot Duration: {self.slot_duration}m)"
