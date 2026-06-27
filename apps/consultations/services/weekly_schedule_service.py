import datetime
from django.db import transaction
from apps.consultations.models.clinic_weekly_schedule import ClinicWeeklySchedule
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.choices import Weekday

class WeeklyScheduleService:

    @classmethod
    def get_schedule(cls) -> list:
        """
        Retrieves all 7 weekdays of the schedule, auto-populating if missing.
        """
        weekdays = [choice[0] for choice in Weekday.choices]
        schedules = []
        for day in weekdays:
            schedule, created = ClinicWeeklySchedule.objects.get_or_create(
                weekday=day,
                defaults={
                    "is_open": day != Weekday.SUNDAY,
                    "opening_time": datetime.time(9, 0) if day != Weekday.SUNDAY else None,
                    "closing_time": datetime.time(18, 0) if day != Weekday.SUNDAY else None,
                }
            )
            schedules.append(schedule)

        # Ensure correct ordering
        weekday_order = {choice[0]: idx for idx, choice in enumerate(Weekday.choices)}
        schedules.sort(key=lambda x: weekday_order.get(x.weekday, 99))
        return schedules

    @classmethod
    @transaction.atomic
    def bulk_update(cls, user, ip_address: str, data_list: list) -> list:
        """
        Bulk updates all seven weekdays in a single atomic transaction.
        """
        # Ensure they exist first
        cls.get_schedule()

        previous_schedule = list(ClinicWeeklySchedule.objects.all())
        previous_values = {
            s.weekday: {
                "is_open": s.is_open,
                "opening_time": str(s.opening_time) if s.opening_time else None,
                "closing_time": str(s.closing_time) if s.closing_time else None,
            } for s in previous_schedule
        }

        updated_instances = []
        changed_details = []

        for item in data_list:
            weekday = item.get("weekday")
            schedule = ClinicWeeklySchedule.objects.get(weekday=weekday)

            is_open = item.get("is_open")
            opening_time = item.get("opening_time")
            closing_time = item.get("closing_time")

            schedule.is_open = is_open
            schedule.opening_time = opening_time if is_open else None
            schedule.closing_time = closing_time if is_open else None

            schedule.full_clean()
            schedule.save()
            updated_instances.append(schedule)

            # Compare to detect changes
            prev = previous_values[weekday]
            new_val = {
                "is_open": is_open,
                "opening_time": str(schedule.opening_time) if schedule.opening_time else None,
                "closing_time": str(schedule.closing_time) if schedule.closing_time else None,
            }
            if prev != new_val:
                changed_details.append(f"{weekday} (Open: {prev['is_open']} -> {is_open})")

        if changed_details:
            desc = f"Weekly schedule updated by {user.email}. Details: {', '.join(changed_details)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.WEEKLY_SCHEDULE_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        # Sort the output
        weekday_order = {choice[0]: idx for idx, choice in enumerate(Weekday.choices)}
        updated_instances.sort(key=lambda x: weekday_order.get(x.weekday, 99))
        return updated_instances
