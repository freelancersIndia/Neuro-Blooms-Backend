from django.db import transaction
from apps.consultations.models.clinic_holiday import ClinicHoliday
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class ClinicHolidayService:

    @classmethod
    def list_holidays(cls) -> list:
        """
        Retrieves all active holidays sorted by date.
        """
        return ClinicHoliday.objects.filter(is_active=True).order_by("holiday_date")

    @classmethod
    @transaction.atomic
    def create_holiday(cls, user, ip_address: str, data: dict) -> ClinicHoliday:
        """
        Creates a new holiday and writes an activity log.
        """
        holiday = ClinicHoliday(
            holiday_name=data.get("holiday_name"),
            holiday_date=data.get("holiday_date"),
            description=data.get("description", ""),
            is_active=True
        )
        holiday.full_clean()
        holiday.save()

        desc = f"Clinic holiday '{holiday.holiday_name}' created for {holiday.holiday_date} by {user.email}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CLINIC_HOLIDAY_CREATED,
            description=desc,
            ip_address=ip_address
        )
        return holiday

    @classmethod
    @transaction.atomic
    def update_holiday(cls, user, ip_address: str, holiday_id: str, data: dict) -> ClinicHoliday:
        """
        Updates an existing active holiday and logs modified fields.
        """
        holiday = ClinicHoliday.objects.get(id=holiday_id, is_active=True)

        previous_values = {
            "holiday_name": holiday.holiday_name,
            "holiday_date": str(holiday.holiday_date),
            "description": holiday.description,
        }

        for field, value in data.items():
            setattr(holiday, field, value)

        holiday.full_clean()
        holiday.save()

        new_values = {
            "holiday_name": holiday.holiday_name,
            "holiday_date": str(holiday.holiday_date),
            "description": holiday.description,
        }

        changed_fields = [k for k, v in previous_values.items() if new_values[k] != v]

        if changed_fields:
            desc = f"Clinic holiday '{holiday.holiday_name}' updated by {user.email}. Changed: {', '.join(changed_fields)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.CLINIC_HOLIDAY_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        return holiday

    @classmethod
    @transaction.atomic
    def delete_holiday(cls, user, ip_address: str, holiday_id: str) -> None:
        """
        Soft deletes a holiday by setting is_active=False.
        """
        holiday = ClinicHoliday.objects.get(id=holiday_id, is_active=True)
        holiday.is_active = False
        holiday.save()

        desc = f"Clinic holiday '{holiday.holiday_name}' on {holiday.holiday_date} soft deleted by {user.email}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CLINIC_HOLIDAY_DELETED,
            description=desc,
            ip_address=ip_address
        )
