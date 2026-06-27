import datetime
from django.db import transaction
from apps.consultations.models.clinic_settings import ClinicSettings
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class ClinicSettingsService:

    @classmethod
    def get_settings(cls) -> ClinicSettings:
        """
        Retrieves the singleton ClinicSettings record, creating default settings if missing.
        """
        return cls.create_default_if_missing()

    @classmethod
    def create_default_if_missing(cls) -> ClinicSettings:
        """
        Ensures a default configuration exists in the database.
        """
        settings, created = ClinicSettings.objects.get_or_create(
            is_active=True,
            defaults={
                "clinic_name": "Neuro Blooms Child Development Center",
                "opening_time": datetime.time(9, 0),
                "closing_time": datetime.time(18, 0),
                "slot_duration_minutes": 45,
                "booking_window_days": 20,
                "allow_same_day_booking": True,
                "max_daily_appointments": 25,
                "timezone": "Asia/Kolkata",
            }
        )
        return settings

    @classmethod
    @transaction.atomic
    def update_settings(cls, user, ip_address: str, data: dict) -> ClinicSettings:
        """
        Updates the singleton settings, handles logo replacement/deletion, and logs the change details.
        """
        settings = cls.get_settings()

        # Capture previous state for audit logging
        previous_values = {
            "clinic_name": settings.clinic_name,
            "opening_time": str(settings.opening_time) if settings.opening_time else None,
            "closing_time": str(settings.closing_time) if settings.closing_time else None,
            "slot_duration_minutes": settings.slot_duration_minutes,
            "booking_window_days": settings.booking_window_days,
            "allow_same_day_booking": settings.allow_same_day_booking,
            "max_daily_appointments": settings.max_daily_appointments,
            "timezone": settings.timezone,
            "clinic_logo": settings.clinic_logo.name if settings.clinic_logo else None,
        }

        new_logo = data.get("clinic_logo")
        old_logo_file = None
        if new_logo and settings.clinic_logo:
            old_logo_file = settings.clinic_logo

        # Apply updates
        for field, value in data.items():
            setattr(settings, field, value)

        settings.full_clean()
        settings.save()

        # Deleting old logo after successful database save
        if old_logo_file:
            try:
                old_logo_file.delete(save=False)
            except Exception:
                pass

        new_values = {
            "clinic_name": settings.clinic_name,
            "opening_time": str(settings.opening_time) if settings.opening_time else None,
            "closing_time": str(settings.closing_time) if settings.closing_time else None,
            "slot_duration_minutes": settings.slot_duration_minutes,
            "booking_window_days": settings.booking_window_days,
            "allow_same_day_booking": settings.allow_same_day_booking,
            "max_daily_appointments": settings.max_daily_appointments,
            "timezone": settings.timezone,
            "clinic_logo": settings.clinic_logo.name if settings.clinic_logo else None,
        }

        # Track modified fields
        changed_fields = [k for k, v in previous_values.items() if new_values[k] != v]

        if changed_fields:
            desc = f"Clinic settings updated by {user.email}. Changed fields: {', '.join(changed_fields)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.CLINIC_SETTINGS_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        return settings
