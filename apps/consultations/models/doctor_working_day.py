from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import Weekday

class DoctorWorkingDay(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="working_days",
        verbose_name="Doctor"
    )
    weekday = models.CharField(
        max_length=20,
        choices=Weekday.choices,
        verbose_name="Weekday"
    )
    is_working = models.BooleanField(default=True, verbose_name="Is Working")
    start_time = models.TimeField(null=True, blank=True, verbose_name="Start Time")
    end_time = models.TimeField(null=True, blank=True, verbose_name="End Time")

    class Meta:
        db_table = "consultations_doctor_working_days"
        verbose_name = "Doctor Working Day"
        verbose_name_plural = "Doctor Working Days"
        ordering = ["weekday", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "weekday"],
                name="unique_doctor_weekday"
            ),
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(is_working=False) |
                    models.Q(is_working=True, end_time__gt=models.F("start_time"))
                ),
                name="doctor_working_day_time_check"
            )
        ]
        indexes = [
            models.Index(fields=["doctor", "weekday"], name="idx_docwork_doc_wkday"),
        ]

    def clean(self):
        super().clean()
        if self.is_working:
            if not self.start_time or not self.end_time:
                raise ValidationError("Start and end times are required if the doctor is working on this day.")
            if self.start_time >= self.end_time:
                raise ValidationError("End time must be after start time.")
        else:
            # If not working, clean up timings to avoid confusion
            self.start_time = None
            self.end_time = None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = f"Working ({self.start_time} - {self.end_time})" if self.is_working else "Off"
        return f"Dr. {self.doctor.email} on {self.get_weekday_display()}: {status}"
