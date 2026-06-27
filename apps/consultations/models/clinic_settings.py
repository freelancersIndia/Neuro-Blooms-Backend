from django.db import models
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel

class ClinicSettings(BaseModel):
    clinic_name = models.CharField(max_length=255, verbose_name="Clinic Name")
    clinic_logo = models.ImageField(upload_to="clinic_logos/", null=True, blank=True, verbose_name="Clinic Logo")
    opening_time = models.TimeField(verbose_name="Opening Time")
    closing_time = models.TimeField(verbose_name="Closing Time")
    slot_duration_minutes = models.PositiveIntegerField(default=30, verbose_name="Slot Duration (Minutes)")
    booking_window_days = models.PositiveIntegerField(default=30, verbose_name="Booking Window (Days)")
    allow_same_day_booking = models.BooleanField(default=True, verbose_name="Allow Same Day Booking")
    max_daily_appointments = models.PositiveIntegerField(default=50, verbose_name="Max Daily Appointments")
    timezone = models.CharField(max_length=100, default="UTC", verbose_name="Timezone")

    class Meta:
        db_table = "consultations_clinic_settings"
        verbose_name = "Clinic Settings"
        verbose_name_plural = "Clinic Settings"
        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_clinic_settings"
            ),
            models.CheckConstraint(
                condition=models.Q(slot_duration_minutes__gt=0),
                name="clinic_slot_duration_check"
            ),
            models.CheckConstraint(
                condition=models.Q(booking_window_days__gt=0),
                name="clinic_booking_window_check"
            ),
            models.CheckConstraint(
                condition=models.Q(max_daily_appointments__gt=0),
                name="clinic_max_daily_appointments_check"
            )
        ]

    def clean(self):
        super().clean()
        if self.opening_time and self.closing_time and self.opening_time >= self.closing_time:
            raise ValidationError("Closing time must be after opening time.")
        if self.is_active:
            qs = ClinicSettings.objects.filter(is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("Only one active clinic configuration is allowed.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.clinic_name} Settings (Active: {self.is_active})"
