from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.consultation import Consultation

class ConsultationAuditLog(BaseModel):
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="audit_logs",
        verbose_name="Consultation"
    )
    field_name = models.CharField(max_length=100, verbose_name="Field Name")
    old_value = models.TextField(null=True, blank=True, verbose_name="Old Value")
    new_value = models.TextField(null=True, blank=True, verbose_name="New Value")
    modified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultation_audit_logs",
        verbose_name="Modified By"
    )

    class Meta:
        db_table = "consultations_consultation_audit_logs"
        verbose_name = "Consultation Audit Log"
        verbose_name_plural = "Consultation Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        by_user = self.modified_by.email if self.modified_by else "System"
        return f"Field '{self.field_name}' updated by {by_user} at {self.created_at}"
