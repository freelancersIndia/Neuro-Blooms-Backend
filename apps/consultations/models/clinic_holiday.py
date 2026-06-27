from django.db import models
from apps.consultations.models.base import BaseModel

class ClinicHoliday(BaseModel):
    holiday_name = models.CharField(max_length=150, default="", blank=True, verbose_name="Holiday Name")
    holiday_date = models.DateField(verbose_name="Holiday Date")
    description = models.TextField(blank=True, null=True, verbose_name="Description")

    class Meta:
        db_table = "consultations_clinic_holidays"
        verbose_name = "Clinic Holiday"
        verbose_name_plural = "Clinic Holidays"
        ordering = ["holiday_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["holiday_date"],
                condition=models.Q(is_active=True),
                name="unique_active_holiday_date"
            )
        ]
        indexes = [
            models.Index(fields=["holiday_date"], name="idx_clinichol_date"),
        ]

    def __str__(self):
        return f"{self.holiday_name} ({self.holiday_date})"
