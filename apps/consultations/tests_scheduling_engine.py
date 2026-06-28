import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, UserRole
from apps.accounts.constants.roles import SystemRole
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
    AppointmentTimeline
)
from apps.consultations.choices import (
    Weekday,
    AppointmentStatus,
    BookingSource,
    AppointmentType,
    RelationshipToChild,
    Gender
)
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class SchedulingEngineTestCase(APITestCase):

    def setUp(self):
        # Seed Roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # Create Users
        self.admin_user = User.objects.create_user(
            email="admin@test.com", password="password123", first_name="Admin"
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.receptionist_user = User.objects.create_user(
            email="receptionist@test.com", password="password123", first_name="Receptionist"
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.doctor_user = User.objects.create_user(
            email="doctor@test.com", password="password123", first_name="Doctor"
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Create Patient
        self.patient = Patient.objects.create(
            patient_number="P-999",
            parent_first_name="Jane",
            parent_last_name="Doe",
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number="9876543210",
            email="jane.doe@test.com",
            child_first_name="Jimmy",
            child_last_name="Doe",
            date_of_birth="2020-01-01",
            gender=Gender.MALE,
            address="123 Street"
        )

        # Clean DB
        ClinicSettings.objects.all().delete()
        ClinicWeeklySchedule.objects.all().delete()
        ClinicHoliday.objects.all().delete()
        ClinicBreak.objects.all().delete()
        DoctorAvailability.objects.all().delete()
        DoctorWorkingDay.objects.all().delete()
        DoctorLeave.objects.all().delete()
        DoctorBlockedSlot.objects.all().delete()
        Appointment.objects.all().delete()
        AppointmentTimeline.objects.all().delete()

        # Seed clinic settings: 30 min duration, 30 days booking window, allow same day
        self.clinic_settings = ClinicSettings.objects.create(
            clinic_name="Neuro Blooms Clinic",
            opening_time="09:00:00",
            closing_time="17:00:00",
            slot_duration_minutes=30,
            booking_window_days=30,
            allow_same_day_booking=True,
            max_daily_appointments=100
        )

        # Seed weekly schedule (open Mon-Sat, closed Sun)
        for day in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY, Weekday.SATURDAY]:
            ClinicWeeklySchedule.objects.create(
                weekday=day,
                is_open=True,
                opening_time="09:00:00",
                closing_time="17:00:00"
            )
        ClinicWeeklySchedule.objects.create(
            weekday=Weekday.SUNDAY,
            is_open=False
        )

        # Seed Doctor Availability (accepts appointments, max 10 patients)
        self.doctor_availability = DoctorAvailability.objects.create(
            doctor=self.doctor_user,
            accepts_appointments=True,
            consultation_duration_minutes=30,
            max_daily_patients=10
        )

        # Seed Doctor Working Days (defaults matching clinic)
        for day in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY, Weekday.SATURDAY]:
            DoctorWorkingDay.objects.create(
                doctor=self.doctor_user,
                weekday=day,
                is_working=True,
                start_time="09:00:00",
                end_time="17:00:00"
            )
        DoctorWorkingDay.objects.create(
            doctor=self.doctor_user,
            weekday=Weekday.SUNDAY,
            is_working=False
        )

        # Target date for testing: Let's pick a future Monday.
        # We need a stable future date that is a Monday.
        # 2026-07-20 is a Monday.
        self.test_date = datetime.date(2026, 7, 20)

    # ==========================================
    # 1. AVAILABLE SLOTS GENERATION TESTS
    # ==========================================

    def test_available_slots_clinic_closed(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Sunday 2026-07-19
        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": "2026-07-19"})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Clinic Closed")
        self.assertEqual(len(response.data["data"]["available_slots"]), 0)

    def test_available_slots_holiday(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Create a clinic holiday on our test date
        ClinicHoliday.objects.create(holiday_name="National Day", holiday_date=self.test_date)

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Clinic Holiday")
        self.assertEqual(len(response.data["data"]["available_slots"]), 0)

    def test_available_slots_clinic_breaks(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Create a lunch break 13:00 - 14:00 on Mondays
        ClinicBreak.objects.create(weekday=Weekday.MONDAY, break_name="Lunch", start_time="13:00:00", end_time="14:00:00")

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slots = response.data["data"]["available_slots"]
        # Check that no slot starts at 13:00 or 13:30
        starts = [s["start"] for s in slots]
        self.assertNotIn("13:00", starts)
        self.assertNotIn("13:30", starts)
        # Ensure other slots exist
        self.assertIn("09:00", starts)
        self.assertIn("12:30", starts)
        self.assertIn("14:00", starts)

    def test_available_slots_doctor_unavailable(self):
        self.client.force_authenticate(user=self.receptionist_user)
        self.doctor_availability.accepts_appointments = False
        self.doctor_availability.save()

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Doctor Not Available")
        self.assertEqual(len(response.data["data"]["available_slots"]), 0)

    def test_available_slots_doctor_leave(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Create a leave covering the test date
        DoctorLeave.objects.create(
            doctor=self.doctor_user,
            start_date=self.test_date - datetime.timedelta(days=1),
            end_date=self.test_date + datetime.timedelta(days=1),
            reason="Medical Leave"
        )

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "Doctor on Leave")
        self.assertEqual(len(response.data["data"]["available_slots"]), 0)

    def test_available_slots_blocked_time(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Create a blocked slot 10:00 - 11:00
        DoctorBlockedSlot.objects.create(
            doctor=self.doctor_user,
            block_date=self.test_date,
            start_time="10:00:00",
            end_time="11:00:00",
            reason="Meeting"
        )

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slots = response.data["data"]["available_slots"]
        starts = [s["start"] for s in slots]
        self.assertNotIn("10:00", starts)
        self.assertNotIn("10:30", starts)
        self.assertIn("09:30", starts)
        self.assertIn("11:00", starts)

    def test_available_slots_existing_appointments(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Create an existing confirmed appointment 09:30 - 10:00
        Appointment.objects.create(
            appointment_number="APT-TEST-001",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=self.test_date,
            start_time="09:30:00",
            end_time="10:00:00",
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        slots = response.data["data"]["available_slots"]
        starts = [s["start"] for s in slots]
        self.assertNotIn("09:30", starts)
        self.assertIn("09:00", starts)
        self.assertIn("10:00", starts)

    def test_available_slots_booking_window(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Date outside the 30-day booking window
        outside_date = timezone.localdate() + datetime.timedelta(days=32)

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(outside_date)})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("appointment_date", response.data["errors"])

    def test_available_slots_same_day_booking_disabled(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Disable same day booking
        self.clinic_settings.allow_same_day_booking = False
        self.clinic_settings.save()

        today = timezone.localdate()
        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(today)})
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("appointment_date", response.data["errors"])

    def test_available_slots_max_daily_patients(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Set max daily patients to 2
        self.doctor_availability.max_daily_patients = 2
        self.doctor_availability.save()

        # Create 2 appointments
        for i, start in enumerate(["09:00:00", "09:30:00"]):
            Appointment.objects.create(
                appointment_number=f"APT-MAX-{i}",
                patient=self.patient,
                doctor=self.doctor_user,
                appointment_type=AppointmentType.INITIAL,
                booking_source=BookingSource.RECEPTIONIST,
                status=AppointmentStatus.CONFIRMED,
                appointment_date=self.test_date,
                start_time=start,
                end_time=(datetime.datetime.combine(self.test_date, datetime.time(9, 0)) + datetime.timedelta(minutes=30*(i+1))).time(),
                approved_by=self.admin_user,
                created_by=self.admin_user
            )

        url = reverse("available-slots")
        response = self.client.get(url, {"doctor_id": self.doctor_user.id, "appointment_date": str(self.test_date)})
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["message"], "No Slots Available")
        self.assertEqual(len(response.data["data"]["available_slots"]), 0)

    # ==========================================
    # 2. SLOT VALIDATION TESTS
    # ==========================================

    def test_validate_slot_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("validate-slot")
        data = {
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "10:30"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["data"]["valid"])

    def test_validate_slot_already_booked(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Book the slot
        Appointment.objects.create(
            appointment_number="APT-VAL-001",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=self.test_date,
            start_time="10:30:00",
            end_time="11:00:00",
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        url = reverse("validate-slot")
        data = {
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "10:30"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["valid"])
        self.assertEqual(response.data["data"]["reason"], "Slot already booked.")

    def test_validate_slot_holiday(self):
        self.client.force_authenticate(user=self.receptionist_user)
        ClinicHoliday.objects.create(holiday_name="Holiday", holiday_date=self.test_date)

        url = reverse("validate-slot")
        data = {
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "10:30"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["valid"])
        self.assertEqual(response.data["data"]["reason"], "Clinic Holiday")

    # ==========================================
    # 3. APPOINTMENT BOOKING TESTS
    # ==========================================

    def test_book_appointment_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-booking")
        data = {
            "patient_id": str(self.patient.id),
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "09:30",
            "appointment_type": "INITIAL",
            "notes": "First assessment"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], "CONFIRMED")
        self.assertEqual(response.data["data"]["visit_reason"], "First assessment")

        # Verify timeline entry
        appt_id = response.data["data"]["id"]
        timeline_exists = AppointmentTimeline.objects.filter(appointment_id=appt_id, event="Appointment Confirmed").exists()
        self.assertTrue(timeline_exists)

        # Verify activity log
        log_exists = ActivityLog.objects.filter(action=ActivityType.APPOINTMENT_CREATED, user=self.receptionist_user).exists()
        self.assertTrue(log_exists)

    def test_book_appointment_duplicate_slot(self):
        self.client.force_authenticate(user=self.receptionist_user)
        
        # Book it once
        Appointment.objects.create(
            appointment_number="APT-DUP-001",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=self.test_date,
            start_time="09:30:00",
            end_time="10:00:00",
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        # Try booking again
        url = reverse("appointment-booking")
        data = {
            "patient_id": str(self.patient.id),
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "09:30",
            "appointment_type": "INITIAL",
            "notes": "Second try"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])
        self.assertIn("Selected slot is no longer available", response.data["errors"]["non_field_errors"][0])

    def test_book_appointment_invalid_patient(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-booking")
        data = {
            "patient_id": "00000000-0000-0000-0000-000000000000",
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "09:30",
            "appointment_type": "INITIAL"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient_id", response.data["errors"])

    def test_book_appointment_invalid_doctor(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-booking")
        # Try using receptionist user ID as doctor
        data = {
            "patient_id": str(self.patient.id),
            "doctor_id": str(self.receptionist_user.id),
            "appointment_date": str(self.test_date),
            "start_time": "09:30",
            "appointment_type": "INITIAL"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("doctor_id", response.data["errors"])
