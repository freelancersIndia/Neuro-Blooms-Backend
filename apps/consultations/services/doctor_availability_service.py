from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.consultations.models.doctor_availability import DoctorAvailability
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class DoctorAvailabilityService:

    @classmethod
    def get_availability(cls, doctor_id: str) -> DoctorAvailability:
        """
        Retrieves availability for a doctor, auto-creating a default preference if missing.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        availability, created = DoctorAvailability.objects.get_or_create(
            doctor=doctor,
            is_active=True,
            defaults={
                "consultation_duration_minutes": 30,
                "max_daily_patients": 15,
                "accepts_appointments": True,
            }
        )
        return availability

    @classmethod
    @transaction.atomic
    def update_availability(cls, user, ip_address: str, doctor_id: str, data: dict) -> DoctorAvailability:
        """
        Updates availability preferences and records activity logs.
        """
        availability = cls.get_availability(doctor_id)

        # Capture old values
        previous_values = {
            "accepting_appointments": availability.accepts_appointments,
            "consultation_duration": availability.consultation_duration_minutes,
            "max_daily_patients": availability.max_daily_patients,
        }

        # Translate API field names to model field names
        if "accepts_appointments" in data:
            availability.accepts_appointments = data["accepts_appointments"]
        if "consultation_duration_minutes" in data:
            availability.consultation_duration_minutes = data["consultation_duration_minutes"]
        if "max_daily_patients" in data:
            availability.max_daily_patients = data["max_daily_patients"]

        try:
            availability.full_clean()
            availability.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        new_values = {
            "accepting_appointments": availability.accepts_appointments,
            "consultation_duration": availability.consultation_duration_minutes,
            "max_daily_patients": availability.max_daily_patients,
        }

        changed_fields = [k for k, v in previous_values.items() if new_values[k] != v]

        if changed_fields:
            desc = f"{user.email} updated availability for Dr. {availability.doctor.email}. Changed: {', '.join(changed_fields)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.DOCTOR_AVAILABILITY_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        return availability
