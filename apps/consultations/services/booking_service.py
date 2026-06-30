import datetime
from zoneinfo import ZoneInfo
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db.models import Prefetch

from apps.accounts.models.user import User
from apps.consultations.models.clinic_settings import ClinicSettings
from apps.consultations.models.clinic_weekly_schedule import ClinicWeeklySchedule
from apps.consultations.models.clinic_holiday import ClinicHoliday
from apps.consultations.models.clinic_break import ClinicBreak
from apps.consultations.models.doctor_availability import DoctorAvailability
from apps.consultations.models.doctor_working_day import DoctorWorkingDay
from apps.consultations.models.doctor_leave import DoctorLeave
from apps.consultations.models.doctor_blocked_slot import DoctorBlockedSlot
from apps.consultations.models.appointment import Appointment
from apps.consultations.models.appointment_request import AppointmentRequest

class BookingService:
    @classmethod
    def get_available_dates(cls, doctor_id):
        """
        Calculates availability for all dates in the booking window.
        Returns a list of dictionaries with date, weekday, status, and message.
        """
        # 1. Load ClinicSettings
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        if not clinic_settings:
            raise ValidationError("Clinic configuration missing.")

        # Timezone setup
        tz = ZoneInfo(clinic_settings.timezone)
        local_now = timezone.now().astimezone(tz)
        today = local_now.date()

        # Calculate date range
        booking_window = clinic_settings.booking_window_days
        start_date = today if clinic_settings.allow_same_day_booking else today + datetime.timedelta(days=1)
        end_date = today + datetime.timedelta(days=booking_window)

        # 2. Bulk load all relevant records for this date range
        weekly_schedules = {
            s.weekday: s for s in ClinicWeeklySchedule.objects.filter(is_active=True)
        }
        
        holidays = {
            h.holiday_date for h in ClinicHoliday.objects.filter(
                holiday_date__range=(start_date, end_date), is_active=True
            )
        }

        doctor_availability = DoctorAvailability.objects.filter(
            doctor_id=doctor_id, is_active=True
        ).first()

        working_days = {
            wd.weekday: wd for wd in DoctorWorkingDay.objects.filter(
                doctor_id=doctor_id, is_active=True
            )
        }

        leaves = DoctorLeave.objects.filter(
            doctor_id=doctor_id,
            start_date__lte=end_date,
            end_date__gte=start_date,
            is_active=True
        )

        appointments = Appointment.objects.filter(
            doctor_id=doctor_id,
            appointment_date__range=(start_date, end_date),
            status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_CONSULTATION'],
            is_active=True
        )

        appointments_by_date = {}
        for appt in appointments:
            appointments_by_date.setdefault(appt.appointment_date, []).append(appt)

        # Query active appointment requests for this doctor in the date range
        doctor = User.objects.filter(id=doctor_id).first()
        doctor_name = f"{doctor.first_name or ''} {doctor.last_name or ''}".strip() if doctor else ""
        pref_note = f"[Preferred Doctor: {doctor_name}]"
        
        requests = AppointmentRequest.objects.filter(
            preferred_date__range=(start_date, end_date),
            additional_notes__contains=pref_note,
            status__in=['PENDING', 'APPROVED', 'RESCHEDULED'],
            is_active=True
        )

        requests_by_date = {}
        for req in requests:
            requests_by_date.setdefault(req.preferred_date, []).append(req)

        blocked_slots = DoctorBlockedSlot.objects.filter(
            doctor_id=doctor_id,
            block_date__range=(start_date, end_date),
            is_active=True
        )
        blocked_by_date = {}
        for bs in blocked_slots:
            blocked_by_date.setdefault(bs.block_date, []).append(bs)

        clinic_breaks = ClinicBreak.objects.filter(is_active=True)
        breaks_by_weekday = {}
        for cb in clinic_breaks:
            breaks_by_weekday.setdefault(cb.weekday, []).append(cb)

        # 3. Iterate through each date in the window and evaluate availability
        results = []
        current_date = start_date
        while current_date <= end_date:
            weekday_name = current_date.strftime('%A').upper()
            
            status_val = "AVAILABLE"
            message_val = "Available"

            if not doctor_availability or not doctor_availability.accepts_appointments:
                status_val = "NOT_ACCEPTING_APPOINTMENTS"
                message_val = "Doctor is not accepting appointments"
            elif weekday_name not in weekly_schedules or not weekly_schedules[weekday_name].is_open:
                status_val = "CLINIC_CLOSED"
                message_val = "Clinic closed"
            elif current_date in holidays:
                status_val = "HOLIDAY"
                message_val = "Clinic holiday"
            elif any(l.start_date <= current_date <= l.end_date for l in leaves):
                status_val = "ON_LEAVE"
                message_val = "Doctor on leave"
            elif weekday_name not in working_days or not working_days[weekday_name].is_working:
                status_val = "DOCTOR_OFF"
                message_val = "Doctor off duty"
            else:
                # Check Doctor max patients limit
                max_patients = doctor_availability.max_daily_patients
                day_appointments = appointments_by_date.get(current_date, [])
                day_requests = requests_by_date.get(current_date, [])
                if len(day_appointments) >= max_patients or len(day_requests) >= max_patients:
                    status_val = "FULLY_BOOKED"
                    message_val = "Doctor daily patient limit reached"
                else:
                    # Generate slots for this day and check if at least one remains
                    day_slots = cls._generate_slots_in_memory(
                        doctor_id=doctor_id,
                        date=current_date,
                        clinic_settings=clinic_settings,
                        weekly_schedule=weekly_schedules[weekday_name],
                        working_day=working_days[weekday_name],
                        doctor_availability=doctor_availability,
                        day_appointments=day_appointments,
                        day_blocked_slots=blocked_by_date.get(current_date, []),
                        weekday_breaks=breaks_by_weekday.get(weekday_name, []),
                        day_requests=day_requests,
                        local_now=local_now
                    )
                    if not day_slots:
                        status_val = "FULLY_BOOKED"
                        message_val = "No slots available"

            results.append({
                "date": current_date.strftime('%Y-%m-%d'),
                "weekday": weekday_name,
                "status": status_val,
                "message": message_val
            })
            current_date += datetime.timedelta(days=1)

        return results

    @classmethod
    def get_available_slots(cls, doctor_id, date):
        """
        Returns all bookable slots for a selected date.
        """
        # 1. Doctor exists
        doctor = User.objects.filter(id=doctor_id, user_roles__role__name='DOCTOR', is_active=True).first()
        if not doctor:
            raise ObjectDoesNotExist("Doctor not found.")

        # 2. Clinic settings exists
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        if not clinic_settings:
            raise ValidationError("Clinic configuration missing.")

        # Timezone setup
        tz = ZoneInfo(clinic_settings.timezone)
        local_now = timezone.now().astimezone(tz)
        today = local_now.date()

        # 3. Date inside booking window
        booking_window = clinic_settings.booking_window_days
        start_date = today if clinic_settings.allow_same_day_booking else today + datetime.timedelta(days=1)
        end_date = today + datetime.timedelta(days=booking_window)
        if not (start_date <= date <= end_date):
            raise ValidationError("Requested date is outside the booking window.")

        # 4. Clinic open
        weekday_name = date.strftime('%A').upper()
        weekly_schedule = ClinicWeeklySchedule.objects.filter(weekday=weekday_name, is_open=True, is_active=True).first()
        if not weekly_schedule:
            return [], "Clinic closed"

        # 5. Holiday
        if ClinicHoliday.objects.filter(holiday_date=date, is_active=True).exists():
            return [], "Clinic Holiday"

        # 6. Doctor accepts appointments
        doctor_availability = DoctorAvailability.objects.filter(doctor_id=doctor_id, is_active=True).first()
        if not doctor_availability or not doctor_availability.accepts_appointments:
            return [], "Doctor is not accepting appointments"

        # 7. Doctor working
        working_day = DoctorWorkingDay.objects.filter(doctor_id=doctor_id, weekday=weekday_name, is_working=True, is_active=True).first()
        if not working_day:
            return [], "Doctor off duty"

        # 8. Doctor leave
        if DoctorLeave.objects.filter(doctor_id=doctor_id, start_date__lte=date, end_date__gte=date, is_active=True).exists():
            return [], "Doctor on leave"

        # 9. Max patients
        max_patients = doctor_availability.max_daily_patients
        day_appointments = Appointment.objects.filter(
            doctor_id=doctor_id,
            appointment_date=date,
            status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_CONSULTATION'],
            is_active=True
        )
        
        # Query active appointment requests for this doctor on this date
        doctor_name = f"{doctor.first_name or ''} {doctor.last_name or ''}".strip()
        pref_note = f"[Preferred Doctor: {doctor_name}]"
        day_requests = AppointmentRequest.objects.filter(
            preferred_date=date,
            additional_notes__contains=pref_note,
            status__in=['PENDING', 'APPROVED', 'RESCHEDULED'],
            is_active=True
        )
        
        if day_appointments.count() >= max_patients or day_requests.count() >= max_patients:
            return [], "Doctor daily patient limit reached"

        # Generate slots
        day_blocked_slots = DoctorBlockedSlot.objects.filter(
            doctor_id=doctor_id,
            block_date=date,
            is_active=True
        )
        weekday_breaks = ClinicBreak.objects.filter(weekday=weekday_name, is_active=True)

        slots = cls._generate_slots_in_memory(
            doctor_id=doctor_id,
            date=date,
            clinic_settings=clinic_settings,
            weekly_schedule=weekly_schedule,
            working_day=working_day,
            doctor_availability=doctor_availability,
            day_appointments=list(day_appointments),
            day_blocked_slots=list(day_blocked_slots),
            weekday_breaks=list(weekday_breaks),
            day_requests=list(day_requests),
            local_now=local_now
        )

        formatted_slots = []
        for s in slots:
            start_str = s["start"].strftime('%H:%M')
            end_str = s["end"].strftime('%H:%M')
            display_start = s["start"].strftime('%I:%M %p').lstrip('0')
            display_end = s["end"].strftime('%I:%M %p').lstrip('0')
            formatted_slots.append({
                "start_time": start_str,
                "end_time": end_str,
                "display": f"{display_start} - {display_end}"
            })

        return formatted_slots, "Available slots retrieved successfully."

    @classmethod
    def validate_booking(cls, data):
        """
        Validates all booking rules before request insertion.
        """
        doctor_id = data.get("doctor_id")
        preferred_date = data.get("preferred_date")
        preferred_time_slot = data.get("preferred_time_slot")
        mobile_number = data.get("mobile_number")
        child_dob = data.get("date_of_birth")

        # Age validation
        if child_dob and child_dob > datetime.date.today():
            raise ValidationError({"date_of_birth": "Child's date of birth cannot be in the future."})

        # Date validation
        if preferred_date < datetime.date.today():
            raise ValidationError({"preferred_date": "Preferred appointment date cannot be in the past."})

        # Get available slots for the day (enforces doctor existence, clinic settings, holiday, leave, same-day window, off duty, max patients, etc.)
        try:
            available_slots, message = cls.get_available_slots(doctor_id, preferred_date)
        except ObjectDoesNotExist as e:
            raise ValidationError({"doctor_id": str(e)})
        except ValueError as e:
            raise ValidationError({"non_field_errors": str(e)})
        except ValidationError as e:
            raise ValidationError({"preferred_date": str(e)})

        # If no slots are available, check if it's due to a date-level restriction
        if not available_slots:
            if message in [
                "Clinic closed",
                "Clinic Holiday",
                "Doctor is not accepting appointments",
                "Doctor off duty",
                "Doctor on leave",
                "Doctor daily patient limit reached"
            ]:
                raise ValidationError({"preferred_date": message})

        # Selected slot still available
        selected_slot_exists = any(s["start_time"] == preferred_time_slot for s in available_slots)
        if not selected_slot_exists:
            raise ValidationError({
                "preferred_time_slot": "Selected slot is no longer available. Reason: Slot already booked or unavailable."
            })

        # Duplicate booking prevention:
        # Prevent same mobile number, same doctor, same date, same slot for:
        # - PENDING/APPROVED/RESCHEDULED request
        # - or CONFIRMED/PENDING/CHECKED_IN/IN_CONSULTATION appointment
        duplicate_request_exists = AppointmentRequest.objects.filter(
            preferred_date=preferred_date,
            preferred_time_slot=preferred_time_slot,
            mobile_number=mobile_number,
            status__in=['PENDING', 'APPROVED', 'RESCHEDULED'],
            is_active=True
        ).exists()

        if duplicate_request_exists:
            raise ValidationError({"non_field_errors": "Duplicate booking exists."})

        duplicate_appt_exists = Appointment.objects.filter(
            doctor_id=doctor_id,
            appointment_date=preferred_date,
            start_time=preferred_time_slot,
            patient__mobile_number=mobile_number,
            status__in=['PENDING', 'CONFIRMED', 'CHECKED_IN', 'IN_CONSULTATION'],
            is_active=True
        ).exists()

        if duplicate_appt_exists:
            raise ValidationError({"non_field_errors": "Duplicate booking exists."})

        return True

    @classmethod
    def _generate_slots_in_memory(
        cls,
        doctor_id,
        date,
        clinic_settings,
        weekly_schedule,
        working_day,
        doctor_availability,
        day_appointments,
        day_blocked_slots,
        weekday_breaks,
        day_requests,
        local_now
    ):
        # Determine interval
        start_time = max(weekly_schedule.opening_time, working_day.start_time)
        end_time = min(weekly_schedule.closing_time, working_day.end_time)

        if start_time >= end_time:
            return []

        duration = doctor_availability.consultation_duration_minutes or clinic_settings.slot_duration_minutes
        
        # Generate raw slots
        slots = []
        current_time = start_time
        while True:
            next_time = cls._add_minutes_to_time(current_time, duration)
            if next_time < current_time or next_time > end_time:
                break
            slots.append({
                "start": current_time,
                "end": next_time
            })
            current_time = next_time

        # Remove slots that start within the next 10 minutes if date is today
        today = local_now.date()
        if date == today:
            cutoff_dt = local_now + datetime.timedelta(minutes=10)
            cutoff_time = cutoff_dt.time()
            if cutoff_dt.date() > today:
                return []
            slots = [s for s in slots if s["start"] >= cutoff_time]

        # Remove overlaps with Clinic Breaks
        slots = [
            s for s in slots 
            if not any(s["start"] < cb.end_time and s["end"] > cb.start_time for cb in weekday_breaks)
        ]

        # Remove overlaps with Doctor Blocked Slots
        slots = [
            s for s in slots 
            if not any(s["start"] < bs.end_time and s["end"] > bs.start_time for bs in day_blocked_slots)
        ]

        # Remove overlaps with Appointments
        slots = [
            s for s in slots 
            if not any(s["start"] < appt.end_time and s["end"] > appt.start_time for appt in day_appointments)
        ]

        # Parse and remove overlaps with Appointment Requests
        parsed_requests = []
        for req in day_requests:
            try:
                start_time = datetime.datetime.strptime(req.preferred_time_slot, "%H:%M").time()
                end_time = cls._add_minutes_to_time(start_time, duration)
                parsed_requests.append({"start": start_time, "end": end_time})
            except ValueError:
                continue

        slots = [
            s for s in slots 
            if not any(s["start"] < req["end"] and s["end"] > req["start"] for req in parsed_requests)
        ]

        return slots

    @staticmethod
    def _add_minutes_to_time(t, minutes):
        dummy_date = datetime.date(2000, 1, 1)
        dt = datetime.datetime.combine(dummy_date, t) + datetime.timedelta(minutes=minutes)
        return dt.time()
