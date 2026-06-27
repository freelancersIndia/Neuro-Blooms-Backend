from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.consultations.models.base import BaseModel
from apps.consultations.models.patient import Patient
from apps.consultations.models.appointment_request import AppointmentRequest
from apps.consultations.choices import (
    BookingSource,
    AppointmentType,
    AppointmentStatus,
    Priority,
    ReferralSource
)

class Appointment(BaseModel):
    appointment_number = models.CharField(max_length=50, unique=True, verbose_name="Appointment Number")
    patient = models.ForeignKey(
        Patient,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Patient"
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="appointments",
        verbose_name="Doctor",
        null=True,
        blank=True
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
        max_length=50,
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
    duration_minutes = models.PositiveIntegerField(
        default=30,
        verbose_name="Duration (Minutes)"
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        verbose_name="Priority"
    )
    referral_source = models.CharField(
        max_length=50,
        choices=ReferralSource.choices,
        null=True,
        blank=True,
        verbose_name="Referral Source"
    )
    visit_reason = models.TextField(default="", blank=True, verbose_name="Visit Reason")
    internal_notes = models.TextField(blank=True, null=True, verbose_name="Internal Notes")
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
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="updated_appointments",
        verbose_name="Updated By"
    )

    class Meta:
        db_table = "consultations_appointments"
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"
        ordering = ["-appointment_date", "-start_time"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_time__gt=models.F("start_time")),
                name="appointment_time_check"
            ),
            models.CheckConstraint(
                condition=models.Q(duration_minutes__gt=0),
                name="appointment_duration_check"
            )
        ]
        indexes = [
            models.Index(fields=["doctor"], name="idx_appt_doctor"),
            models.Index(fields=["patient"], name="idx_appt_patient"),
            models.Index(fields=["appointment_date"], name="idx_appt_date"),
            models.Index(fields=["status"], name="idx_appt_status"),
        ]

    def clean(self):
        super().clean()
        if self.start_time and self.end_time and self.start_time >= self.end_time:
            raise ValidationError("End time must be after start time.")
        if self.duration_minutes <= 0:
            raise ValidationError("Duration must be greater than 0 minutes.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        doctor_str = f" with Dr. {self.doctor.email}" if self.doctor else ""
        return f"{self.appointment_number} - {self.patient.child_first_name} {self.patient.child_last_name}{doctor_str} ({self.appointment_date})"
