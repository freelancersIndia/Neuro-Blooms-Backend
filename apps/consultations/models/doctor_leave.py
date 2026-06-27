from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel

class DoctorLeave(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="leaves",
        verbose_name="Doctor"
    )
    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")
    reason = models.TextField(blank=True, null=True, verbose_name="Reason")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_leaves",
        verbose_name="Approved By"
    )

    class Meta:
        db_table = "consultations_doctor_leaves"
        verbose_name = "Doctor Leave"
        verbose_name_plural = "Doctor Leaves"
        ordering = ["start_date"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F("start_date")),
                name="doctor_leave_date_check"
            )
        ]
        indexes = [
            models.Index(fields=["doctor", "start_date", "end_date"], name="idx_docleave_doc_dates"),
        ]

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError("End date must be on or after start date.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dr. {self.doctor.email} Leave ({self.start_date} to {self.end_date})"
