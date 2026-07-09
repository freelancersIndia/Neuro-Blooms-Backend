import datetime
import uuid
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.consultations.models import (
    ClinicSettings,
    ClinicWeeklySchedule,
    ClinicHoliday,
    ClinicBreak,
    DoctorAvailability,
    DoctorWorkingDay,
    DoctorLeave,
    DoctorBlockedSlot,
    Patient,
    Appointment,
    AppointmentTimeline,
    AppointmentRequest,
    PatientTimeline
)
from apps.consultations.choices import Weekday, AppointmentStatus, BookingSource, AppointmentType, AppointmentRequestStatus
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class AppointmentService:

    @classmethod
    def generate_available_slots(cls, doctor_id: str, appointment_date: datetime.date, exclude_appointment_id: str = None) -> dict:
        """
        Generates available appointment slots for a doctor on a given date by evaluating scheduling priority.
        """
        # Ensure doctor exists and is actually a doctor
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor_id": "Doctor must exist and have the Doctor role."})

        # 1. Load Clinic Settings
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        if not clinic_settings:
            raise ValidationError({"non_field_errors": "Active clinic settings not found."})

        today = timezone.localdate()

        # 2. Validate Booking Window
        if appointment_date < today:
            raise ValidationError({"appointment_date": "Appointment date cannot be in the past."})

        max_bookable_date = today + datetime.timedelta(days=clinic_settings.booking_window_days)
        if appointment_date > max_bookable_date:
            raise ValidationError({"appointment_date": f"Appointment date is outside the booking window (max {clinic_settings.booking_window_days} days)."})

        # 3. Validate Same Day Booking
        if appointment_date == today and not clinic_settings.allow_same_day_booking:
            raise ValidationError({"appointment_date": "Same day booking is disabled."})

        # Weekday mapping for queries
        weekday_map = {
            0: Weekday.MONDAY,
            1: Weekday.TUESDAY,
            2: Weekday.WEDNESDAY,
            3: Weekday.THURSDAY,
            4: Weekday.FRIDAY,
            5: Weekday.SATURDAY,
            6: Weekday.SUNDAY
        }
        weekday_enum = weekday_map[appointment_date.weekday()]

        # 4. Check Weekly Schedule
        weekly_sched = ClinicWeeklySchedule.objects.filter(weekday=weekday_enum).first()
        if not weekly_sched or not weekly_sched.is_open:
            return {
                "doctor_id": doctor.id,
                "date": str(appointment_date),
                "available_slots": [],
                "message": "Clinic Closed"
            }

        # 5. Check Clinic Holiday
        holiday = ClinicHoliday.objects.filter(holiday_date=appointment_date, is_active=True).first()
        if holiday:
            return {
                "doctor_id": doctor.id,
                "date": str(appointment_date),
                "available_slots": [],
                "message": "Clinic Holiday"
            }

        # 6. Load Doctor Availability
        from apps.consultations.services.doctor_availability_service import DoctorAvailabilityService
        availability = DoctorAvailabilityService.get_availability(doctor.id)
        if not availability.accepts_appointments:
            return {
                "doctor_id": doctor.id,
                "date": str(appointment_date),
                "available_slots": [],
                "message": "Doctor Not Available"
            }

        # 7. Load Doctor Working Day
        from apps.consultations.services.doctor_working_day_service import DoctorWorkingDayService
        working_days = DoctorWorkingDayService.get_working_days(doctor.id)
        wday = next((wd for wd in working_days if wd.weekday == weekday_enum), None)
        if not wday or not wday.is_working:
            return {
                "doctor_id": doctor.id,
                "date": str(appointment_date),
                "available_slots": [],
                "message": "Doctor is not working on this day."
            }

        # 8. Check Doctor Leave
        on_leave = DoctorLeave.objects.filter(
            doctor=doctor,
            is_active=True,
            start_date__lte=appointment_date,
            end_date__gte=appointment_date
        ).exists()
        if on_leave:
            return {
                "doctor_id": doctor.id,
                "date": str(appointment_date),
                "available_slots": [],
                "message": "Doctor on Leave"
            }

        # 9. Respect Maximum Daily Patients
        active_statuses = [
            AppointmentStatus.CONFIRMED,
            AppointmentStatus.CHECKED_IN,
            AppointmentStatus.IN_CONSULTATION,
            AppointmentStatus.COMPLETED
        ]
        existing_appts = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status__in=active_statuses,
            is_active=True
        )
        if exclude_appointment_id:
            existing_appts = existing_appts.exclude(id=exclude_appointment_id)

        if existing_appts.count() >= availability.max_daily_patients:
            return {
                "doctor_id": doctor.id,
                "date": str(appointment_date),
                "available_slots": [],
                "message": "No Slots Available"
            }

        # 10. Generate Remaining Slots
        # Doctor operating hours
        doctor_start = wday.start_time
        doctor_end = wday.end_time

        slot_duration = clinic_settings.slot_duration_minutes
        duration_delta = datetime.timedelta(minutes=slot_duration)

        # Pre-fetch breaks, blocked slots, and appointments for overlap checking
        breaks = list(ClinicBreak.objects.filter(weekday=weekday_enum, is_active=True))
        blocked_slots = list(DoctorBlockedSlot.objects.filter(doctor=doctor, block_date=appointment_date, is_active=True))
        appts_list = list(existing_appts)

        available_slots = []
        
        # Combine date and time for slot math
        start_dt = datetime.datetime.combine(appointment_date, doctor_start)
        end_dt = datetime.datetime.combine(appointment_date, doctor_end)

        # Get local time if booking same day to filter out past slots
        now_local = timezone.localtime()
        current_time = now_local.time() if appointment_date == today else None

        current_dt = start_dt
        while current_dt + duration_delta <= end_dt:
            slot_start_time = current_dt.time()
            slot_end_time = (current_dt + duration_delta).time()

            # Same-day past slot filter
            if current_time and slot_start_time <= current_time:
                current_dt += duration_delta
                continue

            overlap = False

            # Check clinic breaks overlap
            for brk in breaks:
                if slot_start_time < brk.end_time and slot_end_time > brk.start_time:
                    overlap = True
                    break

            if overlap:
                current_dt += duration_delta
                continue

            # Check doctor blocked slots overlap
            for block in blocked_slots:
                if slot_start_time < block.end_time and slot_end_time > block.start_time:
                    overlap = True
                    break

            if overlap:
                current_dt += duration_delta
                continue

            # Check existing appointments overlap
            for appt in appts_list:
                if slot_start_time < appt.end_time and slot_end_time > appt.start_time:
                    overlap = True
                    break

            if not overlap:
                available_slots.append({
                    "start": slot_start_time.strftime("%H:%M"),
                    "end": slot_end_time.strftime("%H:%M")
                })

            current_dt += duration_delta

        return {
            "doctor_id": doctor.id,
            "date": str(appointment_date),
            "available_slots": available_slots
        }

    @classmethod
    def validate_slot(cls, doctor_id: str, appointment_date: datetime.date, start_time: datetime.time, exclude_appointment_id: str = None) -> dict:
        """
        Validates if a specific slot is available for a doctor on a given date.
        """
        slots_data = cls.generate_available_slots(doctor_id, appointment_date, exclude_appointment_id=exclude_appointment_id)
        
        # If there's a status message indicating closed, holiday, leave, etc.
        if "message" in slots_data and slots_data["message"] in ["Clinic Closed", "Clinic Holiday", "Doctor on Leave", "Doctor Not Available", "No Slots Available"]:
            return {
                "valid": False,
                "reason": slots_data["message"]
            }

        start_str = start_time.strftime("%H:%M")
        for slot in slots_data["available_slots"]:
            if slot["start"] == start_str:
                return {"valid": True}

        return {
            "valid": False,
            "reason": "Slot already booked."
        }

    @classmethod
    @transaction.atomic
    def create_appointment(
        cls,
        user,
        ip_address: str,
        patient_id: str,
        doctor_id: str,
        appointment_date: datetime.date,
        start_time: datetime.time,
        appointment_type: str,
        notes: str = ""
    ) -> Appointment:
        """
        Creates a confirmed appointment after locking the doctor/date combination and verifying availability.
        """
        # Validate patient
        patient = Patient.objects.filter(id=patient_id).first()
        if not patient:
            raise ValidationError({"patient_id": "Patient must exist."})

        # Validate doctor
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor_id": "Doctor must exist and have the Doctor role."})

        # Validate appointment type
        if appointment_type not in AppointmentType.values:
            raise ValidationError({"appointment_type": f"Invalid appointment type. Allowed: {AppointmentType.values}"})

        # Acquire database lock on all appointments for this doctor on this date
        # This prevents race conditions where two concurrent requests try to book the same slot.
        list(Appointment.objects.select_for_update().filter(
            doctor=doctor,
            appointment_date=appointment_date,
            is_active=True
        ))

        # Recheck slot availability
        validation = cls.validate_slot(doctor_id, appointment_date, start_time)
        if not validation["valid"]:
            raise ValidationError({"non_field_errors": [f"Selected slot is no longer available. Reason: {validation['reason']}"]})

        # Retrieve slot duration
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        duration_minutes = clinic_settings.slot_duration_minutes if clinic_settings else 30
        
        # Calculate end_time
        start_dt = datetime.datetime.combine(appointment_date, start_time)
        end_time = (start_dt + datetime.timedelta(minutes=duration_minutes)).time()

        # Determine booking source based on user role
        booking_source = BookingSource.ADMIN_PANEL
        if user.has_role('RECEPTIONIST'):
            booking_source = BookingSource.RECEPTIONIST

        # Generate unique appointment number
        unique_suffix = uuid.uuid4().hex[:6].upper()
        appointment_number = f"APT-{appointment_date.strftime('%Y%m%d')}-{unique_suffix}"

        # Create Appointment
        appointment = Appointment(
            appointment_number=appointment_number,
            patient=patient,
            doctor=doctor,
            appointment_type=appointment_type,
            booking_source=booking_source,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=duration_minutes,
            visit_reason=notes,
            approved_by=user,
            created_by=user,
            is_active=True
        )

        try:
            appointment.full_clean()
            appointment.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        # Create Timeline Entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Appointment Confirmed",
            description=f"Appointment booked via {booking_source.label}.",
            performed_by=user
        )

        # Create Activity Log
        desc = (
            f"{user.email} created appointment {appointment_number} "
            f"for Patient {patient.child_first_name} {patient.child_last_name} "
            f"with Dr. {doctor.email} on {appointment_date} at {start_time.strftime('%H:%M')}."
        )
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_CREATED,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def approve_request(
        cls,
        user,
        ip_address: str,
        request_id: str,
        doctor_id: str,
        appointment_date: datetime.date,
        start_time: datetime.time,
        remarks: str = ""
    ) -> Appointment:
        """
        Approves an appointment request, creates a confirmed appointment, and updates statuses.
        """
        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Request must be in PATIENT_LINKED or PATIENT_CREATED or RESCHEDULED
        allowed_statuses = [
            AppointmentRequestStatus.PATIENT_LINKED,
            AppointmentRequestStatus.PATIENT_CREATED,
            "RESCHEDULED"
        ]
        if request_obj.status not in allowed_statuses:
            raise ValidationError({"non_field_errors": [f"Cannot approve request. Status is {request_obj.status}."]})

        if not request_obj.patient:
            raise ValidationError({"non_field_errors": ["Cannot approve request. No patient is linked or created."]})

        # Create the confirmed appointment using the existing service method
        appointment = cls.create_appointment(
            user=user,
            ip_address=ip_address,
            patient_id=str(request_obj.patient.id),
            doctor_id=doctor_id,
            appointment_date=appointment_date,
            start_time=start_time,
            appointment_type=request_obj.appointment_type,
            notes=remarks or request_obj.primary_concern
        )

        # Update the appointment request status to APPROVED
        request_obj.status = AppointmentRequestStatus.APPROVED
        request_obj.reviewed_by = user
        request_obj.reviewed_at = timezone.now()
        request_obj.save()

        # Update the appointment to reference the request
        appointment.appointment_request = request_obj
        appointment.save()

        # Create PatientTimeline entry
        PatientTimeline.objects.create(
            patient=request_obj.patient,
            event="Appointment Approved",
            description=f"Appointment request {request_obj.request_number} was approved. Confirmed Appointment: {appointment.appointment_number}.",
            performed_by=user
        )

        # Log Activity
        desc = f"{user.email} approved appointment request {request_obj.request_number} and created appointment {appointment.appointment_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_REQUEST_APPROVED,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def reject_request(
        cls,
        user,
        ip_address: str,
        request_id: str,
        reason: str
    ) -> AppointmentRequest:
        """
        Rejects an appointment request with a mandatory reason.
        """
        if not reason or not reason.strip():
            raise ValidationError({"reason": "Rejection reason is required."})
        if len(reason) > 500:
            raise ValidationError({"reason": "Rejection reason cannot exceed 500 characters."})

        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Cannot reject already approved, completed, or rejected requests
        if request_obj.status == AppointmentRequestStatus.APPROVED:
            raise ValidationError({"non_field_errors": ["Cannot reject an already approved request."]})
        if request_obj.status == AppointmentRequestStatus.REJECTED:
            raise ValidationError({"non_field_errors": ["Cannot reject an already rejected request."]})

        # Update status
        request_obj.status = AppointmentRequestStatus.REJECTED
        request_obj.rejection_reason = reason
        request_obj.reviewed_by = user
        request_obj.reviewed_at = timezone.now()
        request_obj.save()

        # Create PatientTimeline entry (if patient is linked/created)
        if request_obj.patient:
            PatientTimeline.objects.create(
                patient=request_obj.patient,
                event="Appointment Request Rejected",
                description=f"Appointment request {request_obj.request_number} was rejected. Reason: {reason}",
                performed_by=user
            )

        # Log Activity
        desc = f"{user.email} rejected appointment request {request_obj.request_number}. Reason: {reason}"
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_REQUEST_REJECTED,
            description=desc,
            ip_address=ip_address
        )

        return request_obj

    @classmethod
    @transaction.atomic
    def reschedule_request(
        cls,
        user,
        ip_address: str,
        request_id: str,
        doctor_id: str,
        appointment_date: datetime.date,
        start_time: datetime.time,
        reason: str = ""
    ) -> AppointmentRequest:
        """
        Reschedules an appointment request by selecting a new preferred slot.
        """
        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Cannot reschedule if already approved
        if request_obj.status == AppointmentRequestStatus.APPROVED:
            raise ValidationError({"non_field_errors": ["Cannot reschedule an already approved request."]})

        # Validate slot
        validation = cls.validate_slot(doctor_id, appointment_date, start_time)
        if not validation["valid"]:
            raise ValidationError({"non_field_errors": [f"Selected slot is not available. Reason: {validation['reason']}"]})

        # Get doctor
        doctor = User.objects.filter(id=doctor_id).first()
        if not doctor or not doctor.has_role('DOCTOR'):
            raise ValidationError({"doctor_id": "Doctor must exist and have the Doctor role."})

        # Update request preferred slot details
        old_date = request_obj.preferred_date
        old_time = request_obj.preferred_time_slot
        old_status = request_obj.status

        request_obj.preferred_date = appointment_date
        request_obj.preferred_time_slot = f"{start_time.strftime('%H:%M')}"
        request_obj.status = "RESCHEDULED"
        request_obj.save()

        # Create PatientTimeline entry
        if request_obj.patient:
            PatientTimeline.objects.create(
                patient=request_obj.patient,
                event="Appointment Rescheduled",
                description=f"Appointment request rescheduled from {old_date} {old_time} to {appointment_date} {start_time.strftime('%H:%M')}. Reason: {reason}",
                performed_by=user
            )

        # Create Request-Specific Timeline and Activity Logs
        from apps.consultations.services.appointment_request_service import AppointmentRequestService
        from apps.consultations.choices import AppointmentRequestTimelineEvent

        AppointmentRequestService.log_timeline(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.RESCHEDULED,
            title="Rescheduled",
            description=f"Preferred slot changed from {old_date} ({old_time}) to {appointment_date} ({start_time.strftime('%H:%M')}). Reason: {reason}",
            performed_by=user,
            icon="event",
            color="orange",
            metadata={"old_date": str(old_date), "old_slot": old_time, "new_date": str(appointment_date), "new_slot": start_time.strftime('%H:%M'), "reason": reason}
        )

        AppointmentRequestService.log_activity(
            appointment_request=request_obj,
            action="Status Changed",
            performed_by=user,
            old_values={"preferred_date": str(old_date), "preferred_time_slot": old_time, "status": old_status},
            new_values={"preferred_date": str(appointment_date), "preferred_time_slot": start_time.strftime('%H:%M'), "status": "RESCHEDULED"},
            ip_address=ip_address
        )

        # Log Activity
        desc = f"{user.email} rescheduled appointment request {request_obj.request_number} to {appointment_date} at {start_time.strftime('%H:%M')}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_RESCHEDULED,
            description=desc,
            ip_address=ip_address
        )

        return request_obj

    @classmethod
    @transaction.atomic
    def update_appointment(
        cls,
        user,
        ip_address: str,
        appointment_id: str,
        data: dict
    ) -> Appointment:
        """
        Edits a confirmed appointment. Re-validates slot if doctor, date, or time changes.
        """
        appointment = Appointment.objects.select_for_update().filter(id=appointment_id).first()
        if not appointment:
            raise ValidationError({"appointment_id": "Appointment not found."})

        # Cannot edit completed or cancelled appointments
        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise ValidationError({"non_field_errors": [f"Cannot edit appointment in {appointment.status} status."]})

        old_values = {
            "doctor": str(appointment.doctor.id) if appointment.doctor else None,
            "appointment_date": str(appointment.appointment_date),
            "start_time": appointment.start_time.strftime('%H:%M') if appointment.start_time else None,
            "appointment_type": appointment.appointment_type,
            "notes": appointment.visit_reason
        }

        # Track if slot-related fields are changing
        slot_changed = False
        new_doctor_id = data.get("doctor_id", None)
        new_date = data.get("appointment_date", None)
        new_time = data.get("start_time", None)

        if new_doctor_id and str(new_doctor_id) != str(old_values["doctor"]):
            slot_changed = True
            doctor = User.objects.filter(id=new_doctor_id).first()
            if not doctor or not doctor.has_role('DOCTOR'):
                raise ValidationError({"doctor_id": "Doctor must exist and have the Doctor role."})
            appointment.doctor = doctor

        if new_date and new_date != appointment.appointment_date:
            slot_changed = True
            appointment.appointment_date = new_date

        if new_time and new_time != appointment.start_time:
            slot_changed = True
            appointment.start_time = new_time

        if slot_changed:
            # Recheck slot availability
            validation = cls.validate_slot(
                appointment.doctor.id,
                appointment.appointment_date,
                appointment.start_time,
                exclude_appointment_id=appointment.id
            )
            if not validation["valid"]:
                raise ValidationError({"non_field_errors": [f"Selected slot is not available. Reason: {validation['reason']}"]})

            # Recalculate end_time
            clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
            duration_minutes = clinic_settings.slot_duration_minutes if clinic_settings else 30
            start_dt = datetime.datetime.combine(appointment.appointment_date, appointment.start_time)
            appointment.end_time = (start_dt + datetime.timedelta(minutes=duration_minutes)).time()
            appointment.duration_minutes = duration_minutes

        if "appointment_type" in data:
            appt_type = data["appointment_type"]
            if appt_type not in AppointmentType.values:
                raise ValidationError({"appointment_type": f"Invalid appointment type. Allowed: {AppointmentType.values}"})
            appointment.appointment_type = appt_type

        if "notes" in data:
            appointment.visit_reason = data["notes"]

        appointment.updated_by = user
        try:
            appointment.full_clean()
            appointment.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        # Create AppointmentTimeline entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Appointment Edited",
            description="Appointment details were updated.",
            performed_by=user
        )

        # Log Activity
        new_values = {
            "doctor": str(appointment.doctor.id) if appointment.doctor else None,
            "appointment_date": str(appointment.appointment_date),
            "start_time": appointment.start_time.strftime('%H:%M') if appointment.start_time else None,
            "appointment_type": appointment.appointment_type,
            "notes": appointment.visit_reason
        }
        desc = f"{user.email} updated appointment {appointment.appointment_number}. Changes: Old={old_values}, New={new_values}"
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_UPDATED,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def reschedule_appointment(
        cls,
        user,
        ip_address: str,
        appointment_id: str,
        appointment_date: datetime.date,
        start_time: datetime.time,
        reason: str = ""
    ) -> Appointment:
        """
        Moves a confirmed appointment to a new date and time.
        """
        appointment = Appointment.objects.select_for_update().filter(id=appointment_id).first()
        if not appointment:
            raise ValidationError({"appointment_id": "Appointment not found."})

        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED]:
            raise ValidationError({"non_field_errors": [f"Cannot reschedule appointment in {appointment.status} status."]})

        # Validate slot
        validation = cls.validate_slot(
            appointment.doctor.id,
            appointment_date,
            start_time,
            exclude_appointment_id=appointment.id
        )
        if not validation["valid"]:
            raise ValidationError({"non_field_errors": [f"Selected slot is not available. Reason: {validation['reason']}"]})

        old_date = appointment.appointment_date
        old_time = appointment.start_time

        appointment.appointment_date = appointment_date
        appointment.start_time = start_time
        appointment.status = AppointmentStatus.RESCHEDULED

        # Recalculate end_time
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        duration_minutes = clinic_settings.slot_duration_minutes if clinic_settings else 30
        start_dt = datetime.datetime.combine(appointment_date, start_time)
        appointment.end_time = (start_dt + datetime.timedelta(minutes=duration_minutes)).time()
        appointment.duration_minutes = duration_minutes

        appointment.updated_by = user
        try:
            appointment.full_clean()
            appointment.save()
        except DjangoValidationError as e:
            raise ValidationError(e.message_dict)

        # Create AppointmentTimeline entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Appointment Rescheduled",
            description=f"Appointment rescheduled from {old_date} {old_time.strftime('%H:%M')} to {appointment_date} {start_time.strftime('%H:%M')}. Reason: {reason}",
            performed_by=user
        )

        # Log Activity
        desc = f"{user.email} rescheduled appointment {appointment.appointment_number} from {old_date} {old_time.strftime('%H:%M')} to {appointment_date} at {start_time.strftime('%H:%M')}. Reason: {reason}"
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_RESCHEDULED,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def cancel_appointment(
        cls,
        user,
        ip_address: str,
        appointment_id: str,
        reason: str
    ) -> Appointment:
        """
        Cancels a confirmed appointment.
        """
        if not reason or not reason.strip():
            raise ValidationError({"reason": "Cancellation reason is required."})

        appointment = Appointment.objects.select_for_update().filter(id=appointment_id).first()
        if not appointment:
            raise ValidationError({"appointment_id": "Appointment not found."})

        if appointment.status == AppointmentStatus.CANCELLED:
            raise ValidationError({"non_field_errors": ["Appointment is already cancelled."]})
        if appointment.status == AppointmentStatus.COMPLETED:
            raise ValidationError({"non_field_errors": ["Cannot cancel a completed appointment."]})

        appointment.status = AppointmentStatus.CANCELLED
        appointment.internal_notes = f"Cancellation Reason: {reason}"
        appointment.updated_by = user
        appointment.save()

        # Create AppointmentTimeline entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Appointment Cancelled",
            description=f"Appointment cancelled. Reason: {reason}",
            performed_by=user
        )

        # Log Activity
        desc = f"{user.email} cancelled appointment {appointment.appointment_number}. Reason: {reason}"
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_CANCELLED,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def check_in_appointment(
        cls,
        user,
        ip_address: str,
        appointment_id: str
    ) -> Appointment:
        """
        Checks in the patient for their appointment.
        """
        appointment = Appointment.objects.select_for_update().filter(id=appointment_id).first()
        if not appointment:
            raise ValidationError({"appointment_id": "Appointment not found."})

        if appointment.status != AppointmentStatus.CONFIRMED:
            raise ValidationError({"non_field_errors": [f"Only CONFIRMED appointments can be checked in. Current status: {appointment.status}"]})

        appointment.status = AppointmentStatus.CHECKED_IN
        appointment.updated_by = user
        appointment.save()

        # Create AppointmentTimeline entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Patient Checked In",
            description="Patient has checked in and is waiting.",
            performed_by=user
        )

        # Log Activity
        desc = f"{user.email} checked in patient for appointment {appointment.appointment_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_CHECKED_IN,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def start_consultation(
        cls,
        user,
        ip_address: str,
        appointment_id: str
    ) -> Appointment:
        """
        Starts the doctor's consultation for the appointment. Only doctors can perform this action.
        """
        if not user.has_role('DOCTOR'):
            raise ValidationError({"non_field_errors": ["Only users with the DOCTOR role can start a consultation."]})

        appointment = Appointment.objects.select_for_update().filter(id=appointment_id).first()
        if not appointment:
            raise ValidationError({"appointment_id": "Appointment not found."})

        if appointment.status not in [AppointmentStatus.CONFIRMED, AppointmentStatus.CHECKED_IN]:
            raise ValidationError({"non_field_errors": [f"Cannot start consultation. Appointment is in {appointment.status} status."] + (["Must be checked in first."] if appointment.status != AppointmentStatus.CONFIRMED else [])})

        if appointment.doctor and appointment.doctor.id != user.id:
            raise ValidationError({"non_field_errors": ["Only the assigned doctor can start this consultation."]})

        appointment.status = AppointmentStatus.IN_CONSULTATION
        appointment.updated_by = user
        appointment.save()

        # Create AppointmentTimeline entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Consultation Started",
            description=f"Dr. {user.email} started the consultation.",
            performed_by=user
        )

        # Log Activity
        desc = f"Dr. {user.email} started consultation for appointment {appointment.appointment_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_IN_CONSULTATION,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def mark_no_show(
        cls,
        user,
        ip_address: str,
        appointment_id: str
    ) -> Appointment:
        """
        Marks the appointment as a no-show.
        """
        appointment = Appointment.objects.select_for_update().filter(id=appointment_id).first()
        if not appointment:
            raise ValidationError({"appointment_id": "Appointment not found."})

        forbidden_statuses = [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]
        if appointment.status in forbidden_statuses:
            raise ValidationError({"non_field_errors": [f"Cannot mark appointment as no-show. Status is {appointment.status}."]})

        appointment.status = AppointmentStatus.NO_SHOW
        appointment.updated_by = user
        appointment.save()

        # Create AppointmentTimeline entry
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Patient Did Not Attend",
            description="Patient did not attend the scheduled appointment.",
            performed_by=user
        )

        # Log Activity
        desc = f"{user.email} marked appointment {appointment.appointment_number} as NO_SHOW."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_NO_SHOW,
            description=desc,
            ip_address=ip_address
        )

        return appointment
