from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.models.patient import Patient
from apps.consultations.models.appointment_request import AppointmentRequest
from apps.consultations.choices import BookingSource, AppointmentType, AppointmentStatus

class Appointment(BaseModel):
    appointment_number = models.CharField(max_length=50, unique=True, verbose_name="Appointment Number")
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Patient"
    )
    appointment_request = models.ForeignKey(
        AppointmentRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="appointments",
        verbose_name="Appointment Request"
    )
    appointment_type = models.CharField(
        max_length=20,
        choices=AppointmentType.choices,
        verbose_name="Appointment Type"
    )
    parent_appointment = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="child_appointments",
        verbose_name="Parent Appointment"
    )
    booking_source = models.CharField(
        max_length=20,
        choices=BookingSource.choices,
        verbose_name="Booking Source"
    )
    status = models.CharField(
        max_length=20,
        choices=AppointmentStatus.choices,
        default=AppointmentStatus.CONFIRMED,
        verbose_name="Status"
    )
    appointment_date = models.DateField(verbose_name="Appointment Date")
    start_time = models.TimeField(verbose_name="Start Time")
    end_time = models.TimeField(verbose_name="End Time")
    reason_for_visit = models.TextField(verbose_name="Reason for Visit")
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="approved_appointments",
        verbose_name="Approved By"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_appointments",
        verbose_name="Created By"
    )

    class Meta:
        db_table = "consultations_appointments"
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["-appointment_date", "-start_time"]
        indexes = [
            models.Index(fields=["appointment_date"], name="idx_appt_date"),
            models.Index(fields=["status"], name="idx_appt_status"),
            models.Index(fields=["patient"], name="idx_appt_patient"),
        ]

    def __str__(self):
        return f"{self.appointment_number} - {self.patient.child_first_name} {self.patient.child_last_name} ({self.appointment_date})"
