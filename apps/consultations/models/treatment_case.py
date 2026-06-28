from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.patient import Patient

class TreatmentCaseStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    FOLLOW_UP_REQUIRED = 'FOLLOW_UP_REQUIRED', 'Follow-up Required'
    FOLLOW_UP_SCHEDULED = 'FOLLOW_UP_SCHEDULED', 'Follow-up Scheduled'
    FOLLOW_UP_COMPLETED = 'FOLLOW_UP_COMPLETED', 'Follow-up Completed'
    CASE_CLOSED = 'CASE_CLOSED', 'Case Closed'

class TreatmentCase(BaseModel):
    patient = models.ForeignKey(
        Patient,
        on_delete=models.CASCADE,
        related_name="treatment_cases",
        verbose_name="Patient"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="treatment_cases",
        verbose_name="Doctor"
    )
    status = models.CharField(
        max_length=50,
        choices=TreatmentCaseStatus.choices,
        default=TreatmentCaseStatus.ACTIVE,
        verbose_name="Status"
    )
    primary_diagnosis = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="Primary Diagnosis"
    )
    closing_summary = models.TextField(
        blank=True,
        null=True,
        verbose_name="Closing Summary"
    )
    outcome = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name="Outcome"
    )
    reopen_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Reopen Reason"
    )
    start_date = models.DateField(
        auto_now_add=True,
        verbose_name="Start Date"
    )
    end_date = models.DateField(
        blank=True,
        null=True,
        verbose_name="End Date"
    )

    class Meta:
        db_table = "consultations_treatment_cases"
        verbose_name = "Treatment Case"
        verbose_name_plural = "Treatment Cases"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Case {self.id} for {self.patient.child_first_name} (Status: {self.status})"
