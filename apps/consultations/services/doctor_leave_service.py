import datetime
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.consultations.models.doctor_leave import DoctorLeave
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class DoctorLeaveService:

    @classmethod
    def list_leaves(cls, doctor_id: str) -> list:
        """
        Lists all active leaves for the doctor.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        return DoctorLeave.objects.filter(doctor=doctor, is_active=True).order_by("start_date")

    @classmethod
    def validate_leave(cls, doctor, start_date, end_date, reason, current_id=None) -> None:
        """
        Validates leave constraints (dates, past check, and overlaps).
        """
        if not start_date or not end_date:
            raise ValidationError("Start date and end date are required.")

        if start_date > end_date:
            raise ValidationError({"end_date": "End date must be on or after start date."})

        if not reason or not reason.strip():
            raise ValidationError({"reason": "Reason is required."})

        if len(reason) > 1000:
            raise ValidationError({"reason": "Reason cannot exceed 1000 characters."})

        # Cannot create leave entirely in the past
        today = timezone.now().date()
        if end_date < today:
            raise ValidationError("Cannot create leave entirely in the past.")

        # Overlap check
        qs = DoctorLeave.objects.filter(doctor=doctor, is_active=True)
        if current_id:
            qs = qs.exclude(id=current_id)

        for existing in qs:
            if start_date <= existing.end_date and end_date >= existing.start_date:
                raise ValidationError({"non_field_errors": ["Leave overlaps another active leave."]})

    @classmethod
    @transaction.atomic
    def create_leave(cls, user, ip_address: str, doctor_id: str, data: dict) -> DoctorLeave:
        """
        Creates a new planned leave for a doctor.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        start_date = data.get("start_date")
        end_date = data.get("end_date")
        reason = data.get("reason", "")

        cls.validate_leave(doctor, start_date, end_date, reason)

        leave = DoctorLeave(
            doctor=doctor,
            start_date=start_date,
            end_date=end_date,
            reason=reason,
            is_active=True
        )
        try:
            leave.full_clean()
            leave.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        desc = f"{user.email} created leave for Dr. {doctor.email} ({start_date} to {end_date})."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.DOCTOR_LEAVE_CREATED,
            description=desc,
            ip_address=ip_address
        )
        return leave

    @classmethod
    @transaction.atomic
    def update_leave(cls, user, ip_address: str, doctor_id: str, leave_id: str, data: dict) -> DoctorLeave:
        """
        Updates an existing leave after validation.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor": "Doctor must exist and have the Doctor role."})

        leave = DoctorLeave.objects.filter(id=leave_id, doctor=doctor, is_active=True).first()
        if not leave:
            raise ValidationError("Leave record not found or inactive.")

        previous_values = {
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "reason": leave.reason,
        }

        start_date = data.get("start_date", leave.start_date)
        end_date = data.get("end_date", leave.end_date)
        reason = data.get("reason", leave.reason)

        cls.validate_leave(doctor, start_date, end_date, reason, current_id=leave.id)

        leave.start_date = start_date
        leave.end_date = end_date
        leave.reason = reason

        try:
            leave.full_clean()
            leave.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        new_values = {
            "start_date": str(leave.start_date),
            "end_date": str(leave.end_date),
            "reason": leave.reason,
        }

        changed_fields = [k for k, v in previous_values.items() if new_values[k] != v]

        if changed_fields:
            desc = f"{user.email} updated leave for Dr. {doctor.email}. Changed: {', '.join(changed_fields)}."
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.DOCTOR_LEAVE_UPDATED,
                description=desc,
                ip_address=ip_address
            )

        return leave

    @classmethod
    @transaction.atomic
    def delete_leave(cls, user, ip_address: str, doctor_id: str, leave_id: str) -> None:
        """
        Soft deletes a leave.
        """
        doctor = User.objects.filter(id=doctor_id).first()
        leave = DoctorLeave.objects.filter(id=leave_id, doctor=doctor, is_active=True).first()
        if not leave:
            raise ValidationError("Leave record not found or inactive.")

        leave.is_active = False
        leave.save()

        desc = f"{user.email} soft-deleted leave for Dr. {doctor.email} ({leave.start_date} to {leave.end_date})."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.DOCTOR_LEAVE_DELETED,
            description=desc,
            ip_address=ip_address
        )
