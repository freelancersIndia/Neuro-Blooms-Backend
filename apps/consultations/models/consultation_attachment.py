from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.consultation import Consultation

class ConsultationAttachment(BaseModel):
    consultation = models.ForeignKey(
        Consultation,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name="Consultation"
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="uploaded_consultation_attachments",
        verbose_name="Uploaded By"
    )
    file = models.FileField(upload_to="consultation_attachments/", verbose_name="Attachment File")
    original_name = models.CharField(max_length=255, verbose_name="Original Name")
    file_size = models.PositiveIntegerField(verbose_name="File Size (Bytes)")
    mime_type = models.CharField(max_length=100, verbose_name="MIME Type")

    class Meta:
        db_table = "consultations_consultation_attachments"
        verbose_name = "Consultation Attachment"
        verbose_name_plural = "Consultation Attachments"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Attachment for Consultation {self.consultation.id} by {self.uploaded_by.email}"
