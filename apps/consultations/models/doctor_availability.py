from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import Weekday

class DoctorAvailability(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availabilities",
        verbose_name="Doctor"
    )
    weekday = models.IntegerField(
        choices=Weekday.choices,
        verbose_name="Weekday"
    )
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    is_available = models.BooleanField(default=True, verbose_name="Is Available")

    class Meta:
        db_table = "consultations_doctor_availabilities"
        verbose_name = "Doctor Availability"
        verbose_name_plural = "Doctor Availabilities"
        ordering = ["weekday", "start_time"]
        indexes = [
            models.Index(fields=["doctor"], name="idx_docavail_doctor"),
            models.Index(fields=["weekday"], name="idx_docavail_weekday"),
        ]

    def __str__(self):
        return f"Dr. {self.doctor.email} - {self.get_weekday_display()} ({self.start_time} - {self.end_time})"
