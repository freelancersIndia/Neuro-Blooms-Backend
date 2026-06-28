import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import Role, UserRole
from apps.accounts.constants.roles import SystemRole
from apps.consultations.models import (
    ClinicSettings,
    ClinicWeeklySchedule,
    DoctorAvailability,
    DoctorWorkingDay,
    DoctorLeave,
    DoctorBlockedSlot,
    Patient,
    Appointment
)
from apps.consultations.choices import (
    Weekday,
    AppointmentStatus,
    BookingSource,
    AppointmentType,
    Priority,
    RelationshipToChild,
    Gender
)

User = get_user_model()

class DoctorSchedulingTestCase(APITestCase):

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

        # Another doctor for isolation testing
        self.other_doctor = User.objects.create_user(
            email="otherdoc@test.com", password="password123", first_name="OtherDoc"
        )
        UserRole.objects.create(user=self.other_doctor, role=self.doctor_role)

        # Clean DB
        ClinicSettings.objects.all().delete()
        ClinicWeeklySchedule.objects.all().delete()
        DoctorAvailability.objects.all().delete()
        DoctorWorkingDay.objects.all().delete()
        DoctorLeave.objects.all().delete()
        DoctorBlockedSlot.objects.all().delete()
        Patient.objects.all().delete()
        Appointment.objects.all().delete()

        # Seed global clinic setup
        ClinicSettings.objects.create(
            clinic_name="Main Clinic",
            opening_time="09:00:00",
            closing_time="18:00:00"
        )
        for day in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY, Weekday.SATURDAY]:
            ClinicWeeklySchedule.objects.create(
                weekday=day,
                is_open=True,
                opening_time="09:00:00",
                closing_time="18:00:00"
            )
        ClinicWeeklySchedule.objects.create(
            weekday=Weekday.SUNDAY,
            is_open=False
        )

    # ==========================================
    # 1. DOCTOR AVAILABILITY PREFERENCES
    # ==========================================

    def test_doctor_availability_retrieve_and_auto_create(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-availability", args=[self.doctor_user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["consultation_duration"], 30)
        self.assertEqual(response.data["data"]["max_daily_patients"], 15)
        self.assertTrue(response.data["data"]["accepting_appointments"])

    def test_doctor_availability_update(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-availability", args=[self.doctor_user.id])

        data = {
            "accepting_appointments": False,
            "consultation_duration": 45,
            "max_daily_patients": 20
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data["data"]["accepting_appointments"])
        self.assertEqual(response.data["data"]["consultation_duration"], 45)
        self.assertEqual(response.data["data"]["max_daily_patients"], 20)

    def test_doctor_availability_invalid_duration(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-availability", args=[self.doctor_user.id])

        response = self.client.patch(url, {"consultation_duration": 25}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("consultation_duration", response.data["errors"])

    def test_doctor_availability_invalid_max_patients(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-availability", args=[self.doctor_user.id])

        response = self.client.patch(url, {"max_daily_patients": 150}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("max_daily_patients", response.data["errors"])

    def test_doctor_availability_unauthorized_user(self):
        url = reverse("doctor-availability", args=[self.doctor_user.id])

        # 1. Anonymous
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # 2. Doctor attempting other doctor's preferences
        self.client.force_authenticate(user=self.other_doctor)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Receptionist Read-Only
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response = self.client.patch(url, {"max_daily_patients": 5})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # 4. Admin full control
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.patch(url, {"max_daily_patients": 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    # ==========================================
    # 2. DOCTOR WORKING DAYS OVERRIDES
    # ==========================================

    def test_doctor_working_days_retrieve_and_auto_create(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-working-days", args=[self.doctor_user.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 7)
        # Verify defaults matches clinic open (SUNDAY is closed)
        sunday = next(x for x in response.data["data"] if x["weekday"] == Weekday.SUNDAY)
        self.assertFalse(sunday["is_working"])

    def test_doctor_working_days_bulk_update_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-working-days", args=[self.doctor_user.id])

        # Trigger retrieve to auto-create
        self.client.get(url)

        working_days = [
            {"weekday": Weekday.MONDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.TUESDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.WEDNESDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.THURSDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.FRIDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.SATURDAY, "is_working": False, "opening_time": None, "closing_time": None},
            {"weekday": Weekday.SUNDAY, "is_working": False, "opening_time": None, "closing_time": None},
        ]
        response = self.client.patch(url, {"working_days": working_days}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        monday = next(x for x in response.data["data"] if x["weekday"] == Weekday.MONDAY)
        self.assertTrue(monday["is_working"])
        self.assertEqual(monday["opening_time"], "10:00:00")
        self.assertEqual(monday["closing_time"], "16:00:00")

    def test_doctor_working_days_outside_clinic_hours(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("doctor-working-days", args=[self.doctor_user.id])
        self.client.get(url)

        # Clinic closes at 18:00, doctor tries to work until 19:00
        working_days = [
            {"weekday": Weekday.MONDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "19:00:00"},
            {"weekday": Weekday.TUESDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.WEDNESDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.THURSDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.FRIDAY, "is_working": True, "opening_time": "10:00:00", "closing_time": "16:00:00"},
            {"weekday": Weekday.SATURDAY, "is_working": False, "opening_time": None, "closing_time": None},
            {"weekday": Weekday.SUNDAY, "is_working": False, "opening_time": None, "closing_time": None},
        ]
        response = self.client.patch(url, {"working_days": working_days}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # 3. DOCTOR LEAVES
    # ==========================================

    def test_doctor_leave_crud(self):
        self.client.force_authenticate(user=self.doctor_user)
        list_url = reverse("doctor-leave-list", args=[self.doctor_user.id])

        # 1. Create
        data = {
            "start_date": "2026-07-10",
            "end_date": "2026-07-15",
            "reason": "Summer Vacation Leave"
        }
        response = self.client.post(list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        leave_id = response.data["data"]["id"]

        # 2. Update
        detail_url = reverse("doctor-leave-detail", args=[self.doctor_user.id, leave_id])
        response = self.client.patch(detail_url, {"reason": "Updated Reason Vacation"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["reason"], "Updated Reason Vacation")

        # 3. Delete (Soft delete verification)
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DoctorLeave.objects.filter(id=leave_id, is_active=True).count(), 0)
        self.assertEqual(DoctorLeave.objects.filter(id=leave_id, is_active=False).count(), 1)

    def test_doctor_leave_overlap(self):
        self.client.force_authenticate(user=self.doctor_user)
        list_url = reverse("doctor-leave-list", args=[self.doctor_user.id])

        # Create first leave
        self.client.post(list_url, {"start_date": "2026-07-10", "end_date": "2026-07-15", "reason": "L1"})

        # Try overlapping leave
        response = self.client.post(list_url, {"start_date": "2026-07-12", "end_date": "2026-07-18", "reason": "L2"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])

    def test_doctor_leave_entirely_in_past(self):
        self.client.force_authenticate(user=self.doctor_user)
        list_url = reverse("doctor-leave-list", args=[self.doctor_user.id])

        # Yesterday's leave
        yesterday = (timezone.now() - datetime.timedelta(days=1)).date()
        two_days_ago = (timezone.now() - datetime.timedelta(days=2)).date()

        data = {"start_date": str(two_days_ago), "end_date": str(yesterday), "reason": "Past leave"}
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # 4. DOCTOR BLOCKED SLOTS
    # ==========================================

    def test_doctor_blocked_slot_crud(self):
        self.client.force_authenticate(user=self.doctor_user)

        # Doctor working hours default Monday is 09:00 - 18:00
        # Trigger retrieve to auto-create DoctorWorkingDay
        self.client.get(reverse("doctor-working-days", args=[self.doctor_user.id]))

        # Need block date on a Monday: 2026-06-29 is a Monday
        list_url = reverse("doctor-blocked-slot-list", args=[self.doctor_user.id])

        data = {
            "block_date": "2026-06-29",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "reason": "Team Meeting"
        }
        response = self.client.post(list_url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        block_id = response.data["data"]["id"]

        # Detail Update
        detail_url = reverse("doctor-blocked-slot-detail", args=[self.doctor_user.id, block_id])
        response = self.client.patch(detail_url, {"reason": "Important Clinic Team Meeting"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["reason"], "Important Clinic Team Meeting")

        # Soft Delete
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(DoctorBlockedSlot.objects.filter(id=block_id, is_active=True).count(), 0)

    def test_doctor_blocked_slot_outside_working_hours(self):
        self.client.force_authenticate(user=self.doctor_user)
        self.client.get(reverse("doctor-working-days", args=[self.doctor_user.id]))

        list_url = reverse("doctor-blocked-slot-list", args=[self.doctor_user.id])

        # Monday starts at 09:00, block starts at 08:00
        data = {
            "block_date": "2026-06-29",
            "start_time": "08:00:00",
            "end_time": "09:00:00",
            "reason": "Early block"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])

    def test_doctor_blocked_slot_leave_conflict(self):
        self.client.force_authenticate(user=self.doctor_user)
        self.client.get(reverse("doctor-working-days", args=[self.doctor_user.id]))

        # Create leave: 2026-07-10 to 2026-07-15
        DoctorLeave.objects.create(
            doctor=self.doctor_user, start_date="2026-07-10", end_date="2026-07-15", reason="Vacation", is_active=True
        )

        list_url = reverse("doctor-blocked-slot-list", args=[self.doctor_user.id])
        data = {
            "block_date": "2026-07-13", # Monday, inside leave dates
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "reason": "Blocked meeting"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])
        self.assertIn("doctor leave", str(response.data["errors"]["non_field_errors"]).lower())

    def test_doctor_blocked_slot_appointment_conflict(self):
        self.client.force_authenticate(user=self.doctor_user)
        self.client.get(reverse("doctor-working-days", args=[self.doctor_user.id]))

        # Create Patient
        patient = Patient.objects.create(
            patient_number="P-123",
            parent_first_name="Jane",
            parent_last_name="Doe",
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number="1234567890",
            email="jane@test.com",
            child_first_name="Jimmy",
            child_last_name="Doe",
            date_of_birth="2020-01-01",
            gender=Gender.MALE,
            address="123 Street"
        )

        # Create confirmed appointment on 2026-06-29, 10:30 to 11:00
        Appointment.objects.create(
            appointment_number="APT-001",
            patient=patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL_CONSULTATION,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date="2026-06-29",
            start_time="10:30:00",
            end_time="11:00:00",
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        list_url = reverse("doctor-blocked-slot-list", args=[self.doctor_user.id])
        data = {
            "block_date": "2026-06-29",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "reason": "Meeting overlapping appointment"
        }
        response = self.client.post(list_url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])
        self.assertEqual(
            response.data["errors"]["non_field_errors"][0],
            "Cannot block time with existing confirmed appointments."
        )
