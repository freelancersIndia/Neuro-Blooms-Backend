from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel

class DoctorBlockedSlot(BaseModel):
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="blocked_slots",
        verbose_name="Doctor"
    )
    block_date = models.DateField(verbose_name="Block Date")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    reason = models.TextField(blank=True, null=True, verbose_name="Reason")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_blocked_slots",
        verbose_name="Created By"
    )

    class Meta:
        db_table = "consultations_doctor_blocked_slots"
        verbose_name = "Doctor Blocked Slot"
        verbose_name_plural = "Doctor Blocked Slots"
        ordering = ["block_date", "start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="doctor_blocked_time_check"
            )
        ]
        indexes = [
            models.Index(fields=["doctor", "block_date"], name="idx_docblock_doc_date"),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Dr. {self.doctor.email} Blocked on {self.block_date} ({self.start_time} - {self.end_time})"
