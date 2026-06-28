from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.appointment import Appointment

class Consultation(BaseModel):
    appointment = models.OneToOneField(
        Appointment,
        on_delete=models.PROTECT,
        related_name="consultation",
        verbose_name="Appointment"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="consultations",
        verbose_name="Doctor"
    )
    consultation_summary = models.TextField(blank=True, null=True, verbose_name="Consultation Summary")
    clinical_observation = models.TextField(blank=True, null=True, verbose_name="Clinical Observation")
    doctor_recommendations = models.TextField(blank=True, null=True, verbose_name="Doctor Recommendations")
    next_review_date = models.DateField(blank=True, null=True, verbose_name="Next Review Date")
    followup_required = models.BooleanField(default=False, verbose_name="Follow-up Required")

    # Structured Clinical Fields
    chief_complaint = models.TextField(blank=True, null=True, max_length=2000, verbose_name="Chief Complaint")
    clinical_findings = models.TextField(blank=True, null=True, max_length=10000, verbose_name="Clinical Findings")
    diagnosis = models.TextField(blank=True, null=True, max_length=3000, verbose_name="Diagnosis")
    treatment_notes = models.TextField(blank=True, null=True, max_length=10000, verbose_name="Treatment Notes")
    recommendations = models.TextField(blank=True, null=True, max_length=5000, verbose_name="Recommendations")
    is_completed = models.BooleanField(default=False, verbose_name="Is Completed")
    
    # Treatment & Follow-up Relationships
    treatment_case = models.ForeignKey(
        'TreatmentCase',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultations",
        verbose_name="Treatment Case"
    )
    previous_consultation = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="next_consultations",
        verbose_name="Previous Consultation"
    )
    requires_followup = models.BooleanField(
        null=True,
        blank=True,
        verbose_name="Requires Follow-up"
    )

    class Meta:
        db_table = "consultations_consultations"
        verbose_name = "Consultation"
        verbose_name_plural = "Consultations"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["doctor"], name="idx_cons_doctor"),
            models.Index(fields=["next_review_date"], name="idx_cons_next_review"),
        ]

    def __str__(self):
        return f"Consultation for {self.appointment.appointment_number} by Dr. {self.doctor.email}"
