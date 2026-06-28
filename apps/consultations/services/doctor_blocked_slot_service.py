import datetime
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.consultations.models.doctor_blocked_slot import DoctorBlockedSlot
from apps.consultations.models.doctor_working_day import DoctorWorkingDay
from apps.consultations.models.doctor_leave import DoctorLeave
from apps.consultations.models.appointment import Appointment
from apps.consultations.choices import Weekday, AppointmentStatus
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class DoctorBlockedSlotService:

    @classmethod
    def list_blocked_slots(cls, doctor_id: str) -> list:
        """
        Lists all active blocked slots for the doctor.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        return DoctorBlockedSlot.objects.filter(doctor=doctor, is_active=True).order_by("block_date", "start_time")

    @classmethod
    def validate_blocked_slot(cls, doctor, block_date, start_time, end_time, reason, current_id=None) -> None:
        """
        Validates blocked slots constraints: date in future/today, end_time > start_time,
        fits within doctor's working hours, no overlapping blocked slots, no overlapping leaves,
        and no overlapping confirmed appointments.
        """
        if not block_date or not start_time or not end_time:
            raise ValidationError("Block date, start time, and end time are required.")

        if start_time >= end_time:
            raise ValidationError({"end_time": "End time must be after start time."})

        today = timezone.now().date()
        if block_date < today:
            raise ValidationError({"block_date": "Block date cannot be in the past."})

        if not reason or not reason.strip():
            raise ValidationError({"reason": "Reason is required."})

        # 1. Fall within doctor's working hours for that weekday
        # Get weekday
        weekday_map = {
            0: Weekday.MONDAY,
            1: Weekday.TUESDAY,
            2: Weekday.WEDNESDAY,
            3: Weekday.THURSDAY,
            4: Weekday.FRIDAY,
            5: Weekday.SATURDAY,
            6: Weekday.SUNDAY
        }
        weekday_enum = weekday_map[block_date.weekday()]

        working_day = DoctorWorkingDay.objects.filter(doctor=doctor, weekday=weekday_enum).first()
        if not working_day or not working_day.is_working:
            raise ValidationError({"non_field_errors": ["Doctor is not working on this day."]})

        if start_time < working_day.start_time or end_time > working_day.end_time:
            raise ValidationError(
                {"non_field_errors": [f"Blocked time must fall within doctor's working hours ({working_day.start_time.strftime('%H:%M')} - {working_day.end_time.strftime('%H:%M')})."]}
            )

        # 2. Cannot overlap another active blocked time
        qs_blocked = DoctorBlockedSlot.objects.filter(doctor=doctor, block_date=block_date, is_active=True)
        if current_id:
            qs_blocked = qs_blocked.exclude(id=current_id)

        for existing in qs_blocked:
            if start_time < existing.end_time and end_time > existing.start_time:
                raise ValidationError({"non_field_errors": ["Blocked time overlaps with another blocked slot."]})

        # 3. Cannot overlap doctor leave
        leave_exists = DoctorLeave.objects.filter(
            doctor=doctor,
            is_active=True,
            start_date__lte=block_date,
            end_date__gte=block_date
        ).exists()
        if leave_exists:
            raise ValidationError({"non_field_errors": ["Cannot block time during doctor leave."]})

        # 4. Cannot overlap existing confirmed appointments
        # Overlap check: appt.start_time < end_time and appt.end_time > start_time
        appointments_exist = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=block_date,
            status=AppointmentStatus.CONFIRMED,
            is_active=True,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).exists()
        if appointments_exist:
            raise ValidationError({"non_field_errors": ["Cannot block time with existing confirmed appointments."]})

    @classmethod
    @transaction.atomic
    def create_blocked_slot(cls, user, ip_address: str, doctor_id: str, data: dict) -> DoctorBlockedSlot:
        """
        Creates a new blocked slot for the doctor after validation.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        block_date = data.get("block_date")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        reason = data.get("reason", "")

        cls.validate_blocked_slot(doctor, block_date, start_time, end_time, reason)

        blocked_slot = DoctorBlockedSlot(
            doctor=doctor,
            block_date=block_date,
            start_time=start_time,
            end_time=end_time,
            reason=reason,
            created_by=user,
            is_active=True
        )
        try:
            blocked_slot.full_clean()
            blocked_slot.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        desc = f"{user.email} blocked schedule for Dr. {doctor.email} on {block_date} ({start_time.strftime('%H:%M')} - {end_time.strftime('%H:%M')})."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.DOCTOR_BLOCKED_SLOT_CREATED,
            description=desc,
            ip_address=ip_address
        )
        return blocked_slot

    @classmethod
    @transaction.atomic
    def update_blocked_slot(cls, user, ip_address: str, doctor_id: str, block_id: str, data: dict) -> DoctorBlockedSlot:
        """
        Updates an existing blocked slot after validation.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        blocked_slot = DoctorBlockedSlot.objects.filter(id=block_id, doctor=doctor, is_active=True).first()
        if not blocked_slot:
            raise ValidationError("Blocked slot record not found or inactive.")

        previous_values = {
            "block_date": str(blocked_slot.block_date),
            "start_time": str(blocked_slot.start_time),
            "end_time": str(blocked_slot.end_time),
            "reason": blocked_slot.reason,
        }

        block_date = data.get("block_date", blocked_slot.block_date)
        start_time = data.get("start_time", blocked_slot.start_time)
        end_time = data.get("end_time", blocked_slot.end_time)
        reason = data.get("reason", blocked_slot.reason)

        cls.validate_blocked_slot(doctor, block_date, start_time, end_time, reason, current_id=blocked_slot.id)

        blocked_slot.block_date = block_date
        blocked_slot.start_time = start_time
        blocked_slot.end_time = end_time
        blocked_slot.reason = reason

        try:
            blocked_slot.full_clean()
            blocked_slot.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        new_values = {
            "block_date": str(blocked_slot.block_date),
            "start_time": str(blocked_slot.start_time),
            "end_time": str(blocked_slot.end_time),
            "reason": blocked_slot.reason,
        }

        changed_fields = [k for k, v in previous_values.items() if new_values[k] != v]

        if changed_fields:
            desc = f"{user.email} updated blocked slot for Dr. {doctor.email}. Changed: {', '.join(changed_fields)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.DOCTOR_BLOCKED_SLOT_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        return blocked_slot

    @classmethod
    @transaction.atomic
    def delete_blocked_slot(cls, user, ip_address: str, doctor_id: str, block_id: str) -> None:
        """
        Soft deletes a blocked slot.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        blocked_slot = DoctorBlockedSlot.objects.filter(id=block_id, doctor=doctor, is_active=True).first()
        if not blocked_slot:
            raise ValidationError("Blocked slot record not found or inactive.")

        blocked_slot.is_active = False
        blocked_slot.save()

        desc = f"{user.email} soft-deleted blocked slot for Dr. {doctor.email} on {blocked_slot.block_date}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.DOCTOR_BLOCKED_SLOT_DELETED,
            description=desc,
            ip_address=ip_address
        )
