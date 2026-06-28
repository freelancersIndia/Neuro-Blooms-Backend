import datetime
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.consultations.models.doctor_working_day import DoctorWorkingDay
from apps.consultations.models.clinic_weekly_schedule import ClinicWeeklySchedule
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.choices import Weekday

User = get_user_model()

class DoctorWorkingDayService:

    @classmethod
    def get_working_days(cls, doctor_id: str) -> list:
        """
        Retrieves all 7 weekdays of the schedule for the doctor, auto-populating if missing.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        weekdays = [choice[0] for choice in Weekday.choices]
        working_days = []
        for day in weekdays:
            # Check clinic weekly schedule to see if it defaults to open/closed
            clinic_sched = ClinicWeeklySchedule.objects.filter(weekday=day).first()
            clinic_open = clinic_sched.is_open if clinic_sched else (day != Weekday.SUNDAY)
            clinic_start = clinic_sched.opening_time if clinic_sched else datetime.time(9, 0)
            clinic_end = clinic_sched.closing_time if clinic_sched else datetime.time(18, 0)

            wday, created = DoctorWorkingDay.objects.get_or_create(
                doctor=doctor,
                weekday=day,
                defaults={
                    "is_working": clinic_open,
                    "start_time": clinic_start if clinic_open else None,
                    "end_time": clinic_end if clinic_open else None,
                }
            )
            working_days.append(wday)

        # Sort the output Mon -> Sun
        weekday_order = {choice[0]: idx for idx, choice in enumerate(Weekday.choices)}
        working_days.sort(key=lambda x: weekday_order.get(x.weekday, 99))
        return working_days

    @classmethod
    def validate_working_day(cls, weekday: str, is_working: bool, start_time, end_time) -> None:
        """
        Validates that doctor working day hours fall within clinic operating hours for that weekday.
        """
        if not is_working:
            return

        if not start_time or not end_time:
            raise ValidationError("Opening and closing times are required if the doctor is working.")

        if start_time >= end_time:
            raise ValidationError("Closing time must be after opening time.")

        # Check clinic weekly schedule
        clinic_sched = ClinicWeeklySchedule.objects.filter(weekday=weekday).first()
        if clinic_sched:
            if not clinic_sched.is_open:
                raise ValidationError(f"Cannot configure working hours on {weekday} because the clinic is closed.")
            if start_time < clinic_sched.opening_time or end_time > clinic_sched.closing_time:
                raise ValidationError(
                    f"Doctor working hours on {weekday} must fall within clinic operating hours "
                    f"({clinic_sched.opening_time.strftime('%H:%M')} - {clinic_sched.closing_time.strftime('%H:%M')})."
                )
        else:
            # Fallback default clinic hours
            if start_time < datetime.time(9, 0) or end_time > datetime.time(18, 0):
                raise ValidationError(f"Doctor working hours on {weekday} must fall within clinic operating hours (09:00 - 18:00).")

    @classmethod
    @transaction.atomic
    def bulk_update(cls, user, ip_address: str, doctor_id: str, data_list: list) -> list:
        """
        Bulk updates all seven weekdays in a single atomic transaction for a doctor.
        """
        # Ensure doctor exists and working days exist
        cls.get_working_days(doctor_id)

        if len(data_list) != 7:
            raise ValidationError("Bulk update must include exactly 7 days of the week.")

        weekdays = [item.get("weekday") for item in data_list]
        if len(set(weekdays)) != 7:
            raise ValidationError("Each weekday must be uniquely represented.")

        doctor = User.objects.get(id=doctor_id)
        previous_schedule = list(DoctorWorkingDay.objects.filter(doctor=doctor))
        previous_values = {
            s.weekday: {
                "is_working": s.is_working,
                "start_time": str(s.start_time) if s.start_time else None,
                "end_time": str(s.end_time) if s.end_time else None,
            } for s in previous_schedule
        }

        updated_instances = []
        changed_details = []

        for item in data_list:
            weekday = item.get("weekday")
            is_working = item.get("is_working")
            # Map API fields (opening_time, closing_time) to model fields (start_time, end_time)
            start_time = item.get("start_time")
            end_time = item.get("end_time")

            cls.validate_working_day(weekday, is_working, start_time, end_time)

            wday = DoctorWorkingDay.objects.get(doctor=doctor, weekday=weekday)
            wday.is_working = is_working
            wday.start_time = start_time if is_working else None
            wday.end_time = end_time if is_working else None

            try:
                wday.full_clean()
                wday.save()
            except DjangoValidationError as e:
                raise ValidationError(e.message_dict)

            updated_instances.append(wday)

            # Audit compare
            prev = previous_values[weekday]
            new_val = {
                "is_working": is_working,
                "start_time": str(wday.start_time) if wday.start_time else None,
                "end_time": str(wday.end_time) if wday.end_time else None,
            }
            if prev != new_val:
                changed_details.append(f"{weekday} (Working: {prev['is_working']} -> {is_working})")

        if changed_details:
            desc = f"{user.email} updated working days for Dr. {doctor.email}. Details: {', '.join(changed_details)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.DOCTOR_WORKING_DAYS_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        # Sort the output Mon -> Sun
        weekday_order = {choice[0]: idx for idx, choice in enumerate(Weekday.choices)}
        updated_instances.sort(key=lambda x: weekday_order.get(x.weekday, 99))
        return updated_instances
