from django.db import models
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import Weekday

class ClinicWeeklySchedule(BaseModel):
    weekday = models.CharField(
        max_length=20,
        choices=Weekday.choices,
        unique=True,
        verbose_name="Weekday"
    )
    is_open = models.BooleanField(default=True, verbose_name="Is Open")
    opening_time = models.TimeField(null=True, blank=True, verbose_name="Opening Time")
    closing_time = models.TimeField(null=True, blank=True, verbose_name="Closing Time")

    class Meta:
        db_table = "consultations_clinic_weekly_schedules"
        verbose_name = "Clinic Weekly Schedule"
        verbose_name_plural = "Clinic Weekly Schedules"
        ordering = ["weekday"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    models.Q(is_open=False) |
                    models.Q(is_open=True, closing_time__gt=models.F("opening_time"))
                ),
                name="clinic_weekly_schedule_time_check"
            )
        ]

    def clean(self):
        super().clean()
        if self.is_open:
            if not self.opening_time or not self.closing_time:
                raise ValidationError("Opening and closing times are required if the clinic is open on this day.")
            if self.opening_time >= self.closing_time:
                raise ValidationError("Closing time must be after opening time.")
        else:
            # If closed, clean up timings to avoid confusion
            self.opening_time = None
            self.closing_time = None

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = f"Open ({self.opening_time} - {self.closing_time})" if self.is_open else "Closed"
        return f"{self.get_weekday_display()}: {status}"
