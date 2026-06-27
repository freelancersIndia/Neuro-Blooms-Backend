from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel

class DoctorAvailability(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="availabilities",
        verbose_name="Doctor"
    )
    consultation_duration_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name="Consultation Duration (Minutes)"
    )
    max_daily_patients = models.PositiveIntegerField(
        default=15,
        verbose_name="Max Daily Patients"
    )
    accepts_appointments = models.BooleanField(
        default=True,
        verbose_name="Accepts Appointments"
    )

    class Meta:
        db_table = "consultations_doctor_availabilities"
        verbose_name = "Doctor Availability"
        verbose_name_plural = "Doctor Availabilities"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(consultation_duration_minutes__gt=0),
                name="doctor_consultation_duration_check"
            ),
            models.CheckConstraint(
                condition=models.Q(max_daily_patients__gte=0),
                name="doctor_max_daily_patients_check"
            ),
            models.UniqueConstraint(
                fields=["doctor", "is_active"],
                condition=models.Q(is_active=True),
                name="unique_active_doctor_availability"
            )
        ]

    def clean(self):
        super().clean()
        if self.consultation_duration_minutes <= 0:
            raise ValidationError("Consultation duration must be greater than 0.")
        if self.is_active:
            qs = DoctorAvailability.objects.filter(doctor=self.doctor, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            if qs.exists():
                raise ValidationError("A doctor can only have one active availability preference record.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dr. {self.doctor.email} Preferences (Duration: {self.consultation_duration_minutes}m, Active: {self.is_active})"
