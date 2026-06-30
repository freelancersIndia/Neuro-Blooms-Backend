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
    AppointmentRequest
)
from apps.consultations.choices import (
    Weekday,
    AppointmentStatus,
    BookingSource,
    AppointmentType,
    RelationshipToChild,
    Gender
)

User = get_user_model()

class BookingAPITestCase(APITestCase):

    def setUp(self):
        # Seed Roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # Create Doctor
        self.doctor_user = User.objects.create_user(
            email="doctor@test.com", password="password123", first_name="Sarah", last_name="Johnson"
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Create Patient
        self.patient = Patient.objects.create(
            patient_number="PAT-00001",
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
        AppointmentRequest.objects.all().delete()

        # Seed clinic settings: 30 min duration, 30 days booking window, allow same day, timezone UTC
        self.clinic_settings = ClinicSettings.objects.create(
            clinic_name="Neuro Blooms Clinic",
            opening_time="09:00:00",
            closing_time="17:00:00",
            slot_duration_minutes=30,
            booking_window_days=30,
            allow_same_day_booking=True,
            max_daily_appointments=100,
            timezone="UTC"
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

        # Seed Doctor Availability (accepts appointments, 30 min duration, 5 max patients)
        self.doctor_availability = DoctorAvailability.objects.create(
            doctor=self.doctor_user,
            consultation_duration_minutes=30,
            max_daily_patients=5,
            accepts_appointments=True
        )

        # Seed Doctor Working Days (working Mon-Fri 09:00 to 17:00, off Sat-Sun)
        for day in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]:
            DoctorWorkingDay.objects.create(
                doctor=self.doctor_user,
                weekday=day,
                is_working=True,
                start_time="09:00:00",
                end_time="17:00:00"
            )
        DoctorWorkingDay.objects.create(
            doctor=self.doctor_user,
            weekday=Weekday.SATURDAY,
            is_working=False
        )
        DoctorWorkingDay.objects.create(
            doctor=self.doctor_user,
            weekday=Weekday.SUNDAY,
            is_working=False
        )

        # Set up URL names
        self.doctors_url = reverse('booking_doctor_list')
        self.available_dates_url = lambda d_id: reverse('booking_available_dates', args=[d_id])
        self.available_slots_url = lambda d_id: reverse('booking_available_slots', args=[d_id])
        self.appointment_request_url = reverse('booking_appointment_request_create')

    def test_get_doctors_api_unauthenticated(self):
        """
        Verify GET /api/v1/doctors/ returns active doctors and is public.
        """
        response = self.client.get(self.doctors_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        
        doctor_data = response.data['data'][0]
        self.assertEqual(doctor_data['id'], str(self.doctor_user.id))
        self.assertEqual(doctor_data['full_name'], "Sarah Johnson")
        self.assertTrue(doctor_data['accepts_appointments'])
        self.assertNotIn('email', doctor_data)
        self.assertNotIn('phone_number', doctor_data)

    def test_get_available_dates_api(self):
        """
        Verify available dates generation from today to booking_window_days.
        """
        # Test active doctor
        response = self.client.get(self.available_dates_url(self.doctor_user.id))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        dates = response.data['data']
        # The window is 30 days, meaning 31 dates total (today + 30 days)
        self.assertEqual(len(dates), 31)

        # Check Sunday is CLINIC_CLOSED
        sunday_dates = [d for d in dates if d['weekday'] == 'SUNDAY']
        for d in sunday_dates:
            self.assertEqual(d['status'], 'CLINIC_CLOSED')
            self.assertEqual(d['message'], 'Clinic closed')

        # Check Saturday is DOCTOR_OFF
        saturday_dates = [d for d in dates if d['weekday'] == 'SATURDAY']
        for d in saturday_dates:
            self.assertEqual(d['status'], 'DOCTOR_OFF')

    def test_clinic_holiday_in_available_dates(self):
        """
        Verify holiday is correctly marked as HOLIDAY.
        """
        holiday_date = datetime.date.today() + datetime.timedelta(days=2)
        # Ensure it is not a Sunday or Saturday to avoid override
        while holiday_date.weekday() in [5, 6]:
            holiday_date += datetime.timedelta(days=1)

        ClinicHoliday.objects.create(
            holiday_name="National Day",
            holiday_date=holiday_date
        )

        response = self.client.get(self.available_dates_url(self.doctor_user.id))
        dates = response.data['data']
        target_date = next(d for d in dates if d['date'] == holiday_date.strftime('%Y-%m-%d'))
        self.assertEqual(target_date['status'], 'HOLIDAY')
        self.assertEqual(target_date['message'], 'Clinic holiday')

    def test_doctor_leave_in_available_dates(self):
        """
        Verify doctor leave is correctly marked as ON_LEAVE.
        """
        leave_date = datetime.date.today() + datetime.timedelta(days=3)
        while leave_date.weekday() in [5, 6]:
            leave_date += datetime.timedelta(days=1)

        DoctorLeave.objects.create(
            doctor=self.doctor_user,
            start_date=leave_date,
            end_date=leave_date,
            reason="Conference"
        )

        response = self.client.get(self.available_dates_url(self.doctor_user.id))
        dates = response.data['data']
        target_date = next(d for d in dates if d['date'] == leave_date.strftime('%Y-%m-%d'))
        self.assertEqual(target_date['status'], 'ON_LEAVE')
        self.assertEqual(target_date['message'], 'Doctor on leave')

    def test_get_available_slots_api(self):
        """
        Verify slots generation and filtering.
        """
        # Pick a weekday (e.g. Wednesday) to test slots
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={target_date}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        slots = response.data['data']
        # 09:00 to 17:00 with 30 min slots = 16 slots
        self.assertEqual(len(slots), 16)
        self.assertEqual(slots[0]['start_time'], "09:00")
        self.assertEqual(slots[0]['display'], "9:00 AM - 9:30 AM")

    def test_get_slots_overlap_blocked_slot_and_appointment(self):
        """
        Verify slots overlapping with blocked slots or appointments are filtered out.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Create a blocked slot at 10:00 - 11:00 (covers 10:00 and 10:30 slots)
        DoctorBlockedSlot.objects.create(
            doctor=self.doctor_user,
            block_date=target_date,
            start_time="10:00:00",
            end_time="11:00:00",
            reason="Meeting"
        )

        # Create a confirmed appointment at 14:00 - 14:30 (covers 14:00 slot)
        # Note: We need a user to act as approved_by/created_by
        Appointment.objects.create(
            appointment_number="APT-10001",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL_CONSULTATION,
            booking_source=BookingSource.WEBSITE,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=target_date,
            start_time="14:00:00",
            end_time="14:30:00",
            approved_by=self.doctor_user,
            created_by=self.doctor_user
        )

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={target_date}"
        response = self.client.get(url)
        slots = response.data['data']
        
        # Verify 10:00, 10:30, and 14:00 slots are removed
        slot_starts = [s['start_time'] for s in slots]
        self.assertNotIn("10:00", slot_starts)
        self.assertNotIn("10:30", slot_starts)
        self.assertNotIn("14:00", slot_starts)
        self.assertIn("09:30", slot_starts)
        self.assertIn("11:00", slot_starts)
        self.assertIn("13:30", slot_starts)
        self.assertIn("14:30", slot_starts)

    def test_get_slots_overlap_clinic_break(self):
        """
        Verify slots overlapping with clinic breaks are filtered out.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Create a clinic break at 12:00 - 13:00 (covers 12:00 and 12:30 slots)
        weekday_name = target_date.strftime('%A').upper()
        ClinicBreak.objects.create(
            weekday=weekday_name,
            break_name="Lunch",
            start_time="12:00:00",
            end_time="13:00:00"
        )

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={target_date}"
        response = self.client.get(url)
        slots = response.data['data']
        
        # Verify 12:00 and 12:30 slots are removed
        slot_starts = [s['start_time'] for s in slots]
        self.assertNotIn("12:00", slot_starts)
        self.assertNotIn("12:30", slot_starts)
        self.assertIn("11:30", slot_starts)
        self.assertIn("13:00", slot_starts)

    def test_get_slots_overlap_appointment_request(self):
        """
        Verify slots overlapping with active AppointmentRequests are filtered out.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Create a pending appointment request for 10:30
        AppointmentRequest.objects.create(
            request_number="REQ-TEST-1",
            parent_first_name="Jane",
            parent_last_name="Doe",
            relationship_to_child="MOTHER",
            mobile_number="9876543210",
            email="jane.doe@example.com",
            child_first_name="Jimmy",
            child_last_name="Doe",
            date_of_birth="2020-01-01",
            gender="MALE",
            appointment_type="INITIAL_CONSULTATION",
            primary_concern="Speech delay.",
            preferred_date=target_date,
            preferred_time_slot="10:30",
            additional_notes="[Preferred Doctor: Sarah Johnson]",
            status="PENDING"
        )

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={target_date}"
        response = self.client.get(url)
        slots = response.data['data']
        
        # Verify 10:30 slot is removed
        slot_starts = [s['start_time'] for s in slots]
        self.assertNotIn("10:30", slot_starts)
        self.assertIn("10:00", slot_starts)
        self.assertIn("11:00", slot_starts)

    def test_get_slots_daily_limit_requests(self):
        """
        Verify that if active requests reach the daily limit, the day is fully booked.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Create 5 pending requests (limit is 5) for different slots
        for i in range(5):
            AppointmentRequest.objects.create(
                request_number=f"REQ-LIMIT-{i}",
                parent_first_name="Jane",
                parent_last_name="Doe",
                relationship_to_child="MOTHER",
                mobile_number="9876543210",
                email="jane@test.com",
                child_first_name="Jimmy",
                child_last_name="Doe",
                date_of_birth="2020-01-01",
                gender="MALE",
                appointment_type="INITIAL_CONSULTATION",
                primary_concern="Speech delay.",
                preferred_date=target_date,
                preferred_time_slot=f"09:{30 if i%2 else 0}0", # different times
                additional_notes="[Preferred Doctor: Sarah Johnson]",
                status="PENDING"
            )

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={target_date}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data'], [])
        self.assertEqual(response.data['message'], "Doctor daily patient limit reached")

    def test_get_slots_no_block_on_rejected_request(self):
        """
        Verify that rejected appointment requests do not block the slot.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Create a rejected request for 10:30
        AppointmentRequest.objects.create(
            request_number="REQ-TEST-REJECTED",
            parent_first_name="Jane",
            parent_last_name="Doe",
            relationship_to_child="MOTHER",
            mobile_number="9876543210",
            email="jane@test.com",
            child_first_name="Jimmy",
            child_last_name="Doe",
            date_of_birth="2020-01-01",
            gender="MALE",
            appointment_type="INITIAL_CONSULTATION",
            primary_concern="Speech delay.",
            preferred_date=target_date,
            preferred_time_slot="10:30",
            additional_notes="[Preferred Doctor: Sarah Johnson]",
            status="REJECTED"
        )

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={target_date}"
        response = self.client.get(url)
        slots = response.data['data']
        
        # Verify 10:30 slot is STILL available
        slot_starts = [s['start_time'] for s in slots]
        self.assertIn("10:30", slot_starts)

    from unittest.mock import patch

    @patch('django.utils.timezone.now')
    def test_same_day_booking_ten_minute_cutoff(self, mock_now):
        """
        Verify same day booking doesn't return slots within next 10 minutes.
        """
        # Set a fixed time: 2026-06-28 10:00:00 UTC
        fixed_dt = datetime.datetime(2026, 6, 28, 10, 0, 0, tzinfo=datetime.timezone.utc)
        mock_now.return_value = fixed_dt

        today = fixed_dt.date()
        weekday_name = today.strftime('%A').upper()
        
        ClinicWeeklySchedule.objects.update_or_create(
            weekday=weekday_name,
            defaults={'is_open': True, 'opening_time': '00:00:00', 'closing_time': '23:59:00'}
        )
        DoctorWorkingDay.objects.update_or_create(
            doctor=self.doctor_user,
            weekday=weekday_name,
            defaults={'is_working': True, 'start_time': '00:00:00', 'end_time': '23:59:00'}
        )

        url = f"{self.available_slots_url(self.doctor_user.id)}?date={today}"
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        slots = response.data['data']
        
        cutoff_time = (fixed_dt + datetime.timedelta(minutes=10)).time()

        for s in slots:
            slot_start = datetime.datetime.strptime(s['start_time'], '%H:%M').time()
            self.assertTrue(slot_start >= cutoff_time)

    def test_create_appointment_request_success(self):
        """
        Verify successful submission of a valid AppointmentRequest.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        payload = {
            "doctor_id": str(self.doctor_user.id),
            "parent_first_name": "Ravi",
            "parent_last_name": "Kumar",
            "relationship_to_child": "FATHER",
            "mobile_number": "9876543210",
            "email": "ravi.kumar@example.com",
            "child_first_name": "Aarav",
            "child_last_name": "Kumar",
            "date_of_birth": "2020-01-01",
            "gender": "MALE",
            "appointment_type": "INITIAL_CONSULTATION",
            "primary_concern": "Speech delay.",
            "preferred_date": str(target_date),
            "preferred_time_slot": "10:30"
        }

        response = self.client.post(self.appointment_request_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertIn("REQ-", response.data['data']['request_number'])
        self.assertEqual(response.data['data']['status'], "PENDING")

        # Confirm notes field has preferred doctor name prepended
        req = AppointmentRequest.objects.get(id=response.data['data']['id'])
        self.assertIn("Preferred Doctor: Sarah Johnson", req.additional_notes)

    def test_create_appointment_request_duplicate_booking(self):
        """
        Verify duplicate booking prevention (same mobile, doctor, date, slot).
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Create first request
        AppointmentRequest.objects.create(
            request_number="REQ-EXISTING-123",
            parent_first_name="Ravi",
            parent_last_name="Kumar",
            relationship_to_child="FATHER",
            mobile_number="9876543210",
            email="ravi.kumar@example.com",
            child_first_name="Aarav",
            child_last_name="Kumar",
            date_of_birth="2020-01-01",
            gender="MALE",
            appointment_type="INITIAL_CONSULTATION",
            primary_concern="Speech delay.",
            preferred_date=target_date,
            preferred_time_slot="10:30",
            status="PENDING"
        )

        payload = {
            "doctor_id": str(self.doctor_user.id),
            "parent_first_name": "Ravi",
            "parent_last_name": "Kumar",
            "relationship_to_child": "FATHER",
            "mobile_number": "9876543210",
            "email": "ravi.kumar@example.com",
            "child_first_name": "Aarav",
            "child_last_name": "Kumar",
            "date_of_birth": "2020-01-01",
            "gender": "MALE",
            "appointment_type": "INITIAL_CONSULTATION",
            "primary_concern": "Speech delay.",
            "preferred_date": str(target_date),
            "preferred_time_slot": "10:30"
        }

        response = self.client.post(self.appointment_request_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn("Duplicate booking exists.", response.data['errors']['non_field_errors'])

    def test_create_appointment_request_max_patients_limit(self):
        """
        Verify booking is rejected if doctor daily patient limit is reached.
        """
        target_date = datetime.date.today() + datetime.timedelta(days=4)
        while target_date.weekday() in [5, 6]:
            target_date += datetime.timedelta(days=1)

        # Seed 5 appointments (max limit is 5)
        for i in range(5):
            Appointment.objects.create(
                appointment_number=f"APT-LIMIT-{i}",
                patient=self.patient,
                doctor=self.doctor_user,
                appointment_type=AppointmentType.INITIAL_CONSULTATION,
                booking_source=BookingSource.WEBSITE,
                status=AppointmentStatus.CONFIRMED,
                appointment_date=target_date,
                start_time=f"1{i}:00:00",
                end_time=f"1{i}:30:00",
                approved_by=self.doctor_user,
                created_by=self.doctor_user
            )

        payload = {
            "doctor_id": str(self.doctor_user.id),
            "parent_first_name": "Ravi",
            "parent_last_name": "Kumar",
            "relationship_to_child": "FATHER",
            "mobile_number": "9876543210",
            "email": "ravi.kumar@example.com",
            "child_first_name": "Aarav",
            "child_last_name": "Kumar",
            "date_of_birth": "2020-01-01",
            "gender": "MALE",
            "appointment_type": "INITIAL_CONSULTATION",
            "primary_concern": "Speech delay.",
            "preferred_date": str(target_date),
            "preferred_time_slot": "10:30"
        }

        response = self.client.post(self.appointment_request_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn("Doctor daily patient limit reached", response.data['errors']['preferred_date'][0])
