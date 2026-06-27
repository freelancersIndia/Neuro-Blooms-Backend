from django.db import models
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import Weekday

class ClinicBreak(BaseModel):
    weekday = models.CharField(
        max_length=20,
        choices=Weekday.choices,
        verbose_name="Weekday"
    )
    break_name = models.CharField(max_length=100, default="", blank=True, verbose_name="Break Title")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")

    class Meta:
        db_table = "consultations_clinic_breaks"
        verbose_name = "Clinic Break"
        verbose_name_plural = "Clinic Breaks"
        ordering = ["weekday", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="clinic_break_time_check"
            )
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.break_name} on {self.get_weekday_display()} ({self.start_time} - {self.end_time})"
