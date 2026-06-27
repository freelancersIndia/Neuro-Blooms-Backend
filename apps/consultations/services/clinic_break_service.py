from django.db import transaction
from rest_framework.exceptions import ValidationError
from apps.consultations.models.clinic_break import ClinicBreak
from apps.consultations.models.clinic_weekly_schedule import ClinicWeeklySchedule
from apps.consultations.services.clinic_settings_service import ClinicSettingsService
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class ClinicBreakService:

    @classmethod
    def list_breaks(cls) -> list:
        """
        Retrieves all active breaks sorted by weekday and start time.
        """
        from apps.consultations.choices import Weekday
        breaks = list(ClinicBreak.objects.filter(is_active=True))
        weekday_order = {choice[0]: idx for idx, choice in enumerate(Weekday.choices)}
        breaks.sort(key=lambda x: (weekday_order.get(x.weekday, 99), x.start_time))
        return breaks

    @classmethod
    def validate_break(cls, weekday: str, start_time, end_time, current_id=None) -> None:
        """
        Validates break times: end_time > start_time, inside operating hours, and not overlapping.
        """
        if start_time >= end_time:
            raise ValidationError({"end_time": "End time must be after start time."})

        # Validate against weekly schedule bounds
        schedule = ClinicWeeklySchedule.objects.filter(weekday=weekday).first()
        if schedule:
            if not schedule.is_open:
                raise ValidationError({"weekday": "Cannot create breaks for a weekday when the clinic is closed."})
            if start_time < schedule.opening_time or end_time > schedule.closing_time:
                raise ValidationError({"non_field_errors": f"Breaks must be inside clinic operating hours ({schedule.opening_time.strftime('%H:%M')} - {schedule.closing_time.strftime('%H:%M')})."})
        else:
            # Fallback to ClinicSettings
            settings = ClinicSettingsService.get_settings()
            if start_time < settings.opening_time or end_time > settings.closing_time:
                raise ValidationError({"non_field_errors": f"Breaks must be inside clinic operating hours ({settings.opening_time.strftime('%H:%M')} - {settings.closing_time.strftime('%H:%M')})."})

        # Check overlap
        qs = ClinicBreak.objects.filter(weekday=weekday, is_active=True)
        if current_id:
            qs = qs.exclude(id=current_id)

        for existing in qs:
            if start_time < existing.end_time and end_time > existing.start_time:
                raise ValidationError({"non_field_errors": "Break overlaps existing break."})

    @classmethod
    @transaction.atomic
    def create_break(cls, user, ip_address: str, data: dict) -> ClinicBreak:
        """
        Creates a clinic break after validation.
        """
        weekday = data.get("weekday")
        break_name = data.get("break_name")
        start_time = data.get("start_time")
        end_time = data.get("end_time")

        cls.validate_break(weekday, start_time, end_time)

        clinic_break = ClinicBreak(
            weekday=weekday,
            break_name=break_name,
            start_time=start_time,
            end_time=end_time,
            is_active=True
        )
        clinic_break.full_clean()
        clinic_break.save()

        desc = f"Clinic break '{clinic_break.break_name}' on {weekday} ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')}) created by {user.email}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CLINIC_BREAK_CREATED,
            description=desc,
            ip_address=ip_address
        )
        return clinic_break

    @classmethod
    @transaction.atomic
    def update_break(cls, user, ip_address: str, break_id: str, data: dict) -> ClinicBreak:
        """
        Updates an existing break after validation.
        """
        clinic_break = ClinicBreak.objects.get(id=break_id, is_active=True)

        previous_values = {
            "weekday": clinic_break.weekday,
            "break_name": clinic_break.break_name,
            "start_time": clinic_break.start_time,
            "end_time": clinic_break.end_time,
        }

        weekday = data.get("weekday", clinic_break.weekday)
        break_name = data.get("break_name", clinic_break.break_name)
        start_time = data.get("start_time", clinic_break.start_time)
        end_time = data.get("end_time", clinic_break.end_time)

        cls.validate_break(weekday, start_time, end_time, current_id=clinic_break.id)

        clinic_break.weekday = weekday
        clinic_break.break_name = break_name
        clinic_break.start_time = start_time
        clinic_break.end_time = end_time

        clinic_break.full_clean()
        clinic_break.save()

        new_values = {
            "weekday": clinic_break.weekday,
            "break_name": clinic_break.break_name,
            "start_time": clinic_break.start_time,
            "end_time": clinic_break.end_time,
        }

        changed_fields = [k for k, v in previous_values.items() if new_values[k] != v]

        if changed_fields:
            desc = f"Clinic break '{clinic_break.break_name}' updated by {user.email}. Changed: {', '.join(changed_fields)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.CLINIC_BREAK_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        return clinic_break

    @classmethod
    @transaction.atomic
    def delete_break(cls, user, ip_address: str, break_id: str) -> None:
        """
        Soft deletes a clinic break.
        """
        clinic_break = ClinicBreak.objects.get(id=break_id, is_active=True)
        clinic_break.is_active = False
        clinic_break.save()

        desc = f"Clinic break '{clinic_break.break_name}' on {clinic_break.weekday} soft deleted by {user.email}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CLINIC_BREAK_DELETED,
            description=desc,
            ip_address=ip_address
        )
