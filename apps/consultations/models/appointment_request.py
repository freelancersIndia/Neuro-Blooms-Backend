from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import (
    Gender,
    RelationshipToChild,
    AppointmentRequestStatus,
    BookingSource,
    AppointmentType,
)

class AppointmentRequest(BaseModel):
    request_number = models.CharField(max_length=50, unique=True, verbose_name="Request Number")
    parent_first_name = models.CharField(max_length=150, verbose_name="Parent First Name")
    parent_last_name = models.CharField(max_length=150, verbose_name="Parent Last Name")
    relationship_to_child = models.CharField(
        max_length=50,
        choices=RelationshipToChild.choices,
        verbose_name="Relationship to Child"
    )
    mobile_number = models.CharField(max_length=20, verbose_name="Mobile Number")
    alternate_mobile_number = models.CharField(max_length=20, blank=True, null=True, verbose_name="Alternate Mobile Number")
    email = models.EmailField(verbose_name="Email Address")
    child_first_name = models.CharField(max_length=150, verbose_name="Child First Name")
    child_last_name = models.CharField(max_length=150, verbose_name="Child Last Name")
    date_of_birth = models.DateField(verbose_name="Child Date of Birth")
    gender = models.CharField(max_length=20, choices=Gender.choices, verbose_name="Gender")
    appointment_type = models.CharField(max_length=50, choices=AppointmentType.choices, verbose_name="Appointment Type")
    primary_concern = models.TextField(verbose_name="Primary Concern")
    preferred_date = models.DateField(verbose_name="Preferred Date")
    preferred_time_slot = models.CharField(max_length=50, verbose_name="Preferred Time Slot")
    additional_notes = models.TextField(blank=True, null=True, verbose_name="Additional Notes")
    referral_source = models.CharField(max_length=255, blank=True, null=True, verbose_name="Referral Source")
    booking_source = models.CharField(
        max_length=20,
        choices=BookingSource.choices,
        default=BookingSource.WEBSITE,
        verbose_name="Booking Source"
    )
    status = models.CharField(
        max_length=20,
        choices=AppointmentRequestStatus.choices,
        default=AppointmentRequestStatus.PENDING,
        verbose_name="Status"
    )
    rejection_reason = models.TextField(blank=True, null=True, verbose_name="Rejection Reason")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_requests',
        verbose_name="Reviewed By"
    )
    reviewed_at = models.DateTimeField(blank=True, null=True, verbose_name="Reviewed At")
    
    patient = models.ForeignKey(
        'Patient',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='appointment_requests',
        verbose_name="Linked/Created Patient"
    )
    patient_linked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='linked_requests',
        verbose_name="Patient Linked By"
    )
    patient_linked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Patient Linked At"
    )
    patient_created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_patient_requests',
        verbose_name="Patient Created By"
    )
    patient_created_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Patient Created At"
    )

    class Meta:
        db_table = "consultations_appointment_requests"
        verbose_name = "Appointment Request"
        verbose_name_plural = "Appointment Requests"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_apptreq_status"),
            models.Index(fields=["mobile_number"], name="idx_apptreq_mobile"),
            models.Index(fields=["preferred_date"], name="idx_apptreq_pref_date"),
            models.Index(fields=["patient"], name="idx_apptreq_patient"),
        ]

    def __str__(self):
        return f"{self.request_number} - {self.child_first_name} {self.child_last_name} ({self.status})"
