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
    consultation_summary = models.TextField(verbose_name="Consultation Summary")
    clinical_observation = models.TextField(verbose_name="Clinical Observation")
    doctor_recommendations = models.TextField(verbose_name="Doctor Recommendations")
    next_review_date = models.DateField(blank=True, null=True, verbose_name="Next Review Date")
    followup_required = models.BooleanField(default=False, verbose_name="Follow-up Required")

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
