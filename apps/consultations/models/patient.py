from django.db import models
from apps.consultations.models.base import BaseModel
from apps.consultations.choices import Gender, RelationshipToChild, PatientStatus

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
        ]

    def __str__(self):
        return f"{self.patient_number} - {self.child_first_name} {self.child_last_name}"
