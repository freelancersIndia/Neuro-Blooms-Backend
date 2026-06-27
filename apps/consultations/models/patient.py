from django.db import models
from django.conf import settings
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import Gender, RelationshipToChild, PatientStatus

class PatientQuerySet(models.QuerySet):
    def active_records(self):
        return self.filter(is_deleted=False)

class PatientManager(models.Manager):
    def get_queryset(self):
        return PatientQuerySet(self.model, using=self._db).active_records()

    def all_with_deleted(self):
        return PatientQuerySet(self.model, using=self._db)

class Patient(BaseModel):
    patient_number = models.CharField(max_length=50, unique=True, verbose_name="Patient Number")
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
    address = models.TextField(verbose_name="Address")
    patient_status = models.CharField(
        max_length=30,
        choices=PatientStatus.choices,
        default=PatientStatus.ACTIVE,
        verbose_name="Patient Status"
    )
    
    # New Fields for Phase 4
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_patients",
        verbose_name="Assigned Doctor"
    )
    emergency_contact_name = models.CharField(max_length=150, blank=True, null=True, verbose_name="Emergency Contact Name")
    emergency_contact_phone = models.CharField(max_length=20, blank=True, null=True, verbose_name="Emergency Contact Phone")
    preferred_language = models.CharField(max_length=50, blank=True, null=True, verbose_name="Preferred Language")
    referral_source = models.CharField(max_length=255, blank=True, null=True, verbose_name="Referral Source")
    primary_diagnosis = models.TextField(blank=True, null=True, verbose_name="Primary Diagnosis")
    notes = models.TextField(blank=True, null=True, verbose_name="Medical Notes")
    photo = models.ImageField(upload_to="patients/", blank=True, null=True, verbose_name="Photo")
    
    # Child Information fields
    blood_group = models.CharField(max_length=10, blank=True, null=True, verbose_name="Blood Group")
    allergies = models.TextField(blank=True, null=True, verbose_name="Allergies")
    medical_alerts = models.TextField(blank=True, null=True, verbose_name="Medical Alerts")

    # Overview Tab fields
    current_focus = models.TextField(blank=True, null=True, verbose_name="Current Focus")
    therapy_started = models.DateField(blank=True, null=True, verbose_name="Therapy Started")
    treatment_summary = models.TextField(blank=True, null=True, verbose_name="Treatment Summary")
    current_progress = models.TextField(blank=True, null=True, verbose_name="Current Progress")
    latest_recommendation = models.TextField(blank=True, null=True, verbose_name="Latest Recommendation")
    current_treatment_plan = models.TextField(blank=True, null=True, verbose_name="Current Treatment Plan")
    
    # Internal Notes field for API 10
    internal_notes = models.TextField(blank=True, null=True, verbose_name="Internal Notes")
    
    # Session counts for API 13
    recommended_sessions = models.IntegerField(default=10, null=True, blank=True, verbose_name="Recommended Sessions")
    
    # Soft Delete & Audit Fields
    is_deleted = models.BooleanField(default=False, verbose_name="Is Deleted")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Deleted At")
    deleted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="deleted_patients",
        verbose_name="Deleted By"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_patients",
        verbose_name="Created By"
    )

    objects = PatientManager()

    class Meta:
        db_table = "consultations_patients"
        verbose_name = "Patient"
        verbose_name_plural = "Patients"
        ordering = ["child_last_name", "child_first_name"]
        indexes = [
            models.Index(fields=["mobile_number"], name="idx_patient_mobile"),
            models.Index(fields=["child_first_name"], name="idx_patient_first_name"),
            models.Index(fields=["child_last_name"], name="idx_patient_last_name"),
            models.Index(fields=["date_of_birth"], name="idx_patient_dob"),
            models.Index(fields=["is_deleted"], name="idx_patient_is_deleted"),
            models.Index(fields=["assigned_doctor"], name="idx_patient_doctor"),
        ]

    def __str__(self):
        return f"{self.patient_number} - {self.child_first_name} {self.child_last_name}"
