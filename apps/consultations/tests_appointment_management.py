import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models import Role, UserRole
from apps.accounts.constants.roles import SystemRole
from apps.consultations.models import (
    AppointmentRequest,
    Patient,
    Appointment,
    AppointmentTimeline,
    PatientTimeline,
    ClinicSettings,
    ClinicWeeklySchedule,
    DoctorAvailability,
    DoctorWorkingDay
)
from apps.consultations.choices import (
    Gender,
    RelationshipToChild,
    AppointmentRequestStatus,
    AppointmentType,
    AppointmentStatus,
    Weekday,
    BookingSource
)
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class AppointmentManagementTestCase(APITestCase):

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

        # Create another doctor
        self.doctor_user_2 = User.objects.create_user(
            email="doctor2@test.com", password="password123", first_name="Doctor2"
        )
        UserRole.objects.create(user=self.doctor_user_2, role=self.doctor_role)

        # Clean DB
        AppointmentRequest.objects.all().delete()
        Patient.objects.all_with_deleted().delete()
        Appointment.objects.all().delete()
        PatientTimeline.objects.all().delete()
        AppointmentTimeline.objects.all().delete()
        ActivityLog.objects.all().delete()

        # Seed Clinic Settings
        self.clinic_settings = ClinicSettings.objects.create(
            clinic_name="Test Clinic",
            opening_time="09:00:00",
            closing_time="17:00:00",
            slot_duration_minutes=30,
            booking_window_days=30,
            allow_same_day_booking=True,
            max_daily_appointments=100,
            is_active=True
        )

        # Seed Weekly Schedule (Open every day)
        for wd in Weekday.values:
            ClinicWeeklySchedule.objects.create(
                weekday=wd,
                is_open=True,
                opening_time="09:00:00",
                closing_time="17:00:00"
            )

        # Setup Doctor Availability & Working Days
        for doc in [self.doctor_user, self.doctor_user_2]:
            DoctorAvailability.objects.create(
                doctor=doc,
                accepts_appointments=True,
                consultation_duration_minutes=30,
                max_daily_patients=10
            )
            for wd in Weekday.values:
                DoctorWorkingDay.objects.create(
                    doctor=doc,
                    weekday=wd,
                    is_working=True,
                    start_time="09:00:00",
                    end_time="17:00:00"
                )

        # Create a patient
        self.patient = Patient.objects.create(
            patient_number="PAT-000001",
            parent_first_name="Ravi",
            parent_last_name="Kumar",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9876543210",
            email="ravi.kumar@test.com",
            child_first_name="Aarav",
            child_last_name="Kumar",
            date_of_birth="2020-01-01",
            gender=Gender.MALE
        )

        # Create an Appointment Request that is linked to the patient
        self.request_linked = AppointmentRequest.objects.create(
            request_number="REQ-2026-00001",
            parent_first_name="Ravi",
            parent_last_name="Kumar",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9876543210",
            email="ravi.kumar@test.com",
            child_first_name="Aarav",
            child_last_name="Kumar",
            date_of_birth="2020-01-01",
            gender=Gender.MALE,
            appointment_type=AppointmentType.INITIAL,
            primary_concern="Speech delay",
            preferred_date="2026-07-20",
            preferred_time_slot="10:00 - 10:30",
            status=AppointmentRequestStatus.PATIENT_LINKED,
            patient=self.patient
        )

    # ==========================================
    # 1. APPOINTMENT REQUEST DECISION TESTS
    # ==========================================

    def test_approve_request_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-approve", kwargs={"id": self.request_linked.id})
        data = {
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": "2026-07-20",
            "start_time": "10:00",
            "remarks": "Approve and book"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])

        # Verify request status updated
        self.request_linked.refresh_from_db()
        self.assertEqual(self.request_linked.status, AppointmentRequestStatus.APPROVED)
        self.assertIsNotNone(self.request_linked.reviewed_at)
        self.assertEqual(self.request_linked.reviewed_by, self.receptionist_user)

        # Verify appointment created
        appt = Appointment.objects.get(appointment_request=self.request_linked)
        self.assertEqual(appt.status, AppointmentStatus.CONFIRMED)
        self.assertEqual(appt.doctor, self.doctor_user)
        self.assertEqual(appt.appointment_date, datetime.date(2026, 7, 20))
        self.assertEqual(appt.start_time, datetime.time(10, 0))

        # Verify timelines
        self.assertTrue(PatientTimeline.objects.filter(patient=self.patient, event="Appointment Approved").exists())
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=appt, event="Appointment Confirmed").exists())

        # Verify activity log
        self.assertTrue(ActivityLog.objects.filter(action=ActivityType.APPOINTMENT_REQUEST_APPROVED, user=self.receptionist_user).exists())

    def test_approve_request_slot_taken(self):
        # First book a slot
        Appointment.objects.create(
            appointment_number="APT-TEST-123",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        # Now try to approve request on the same slot
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-approve", kwargs={"id": self.request_linked.id})
        data = {
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": "2026-07-20",
            "start_time": "10:00"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])

    def test_reject_request_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-reject", kwargs={"id": self.request_linked.id})
        data = {
            "reason": "Doctor unavailable on preferred date."
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.request_linked.refresh_from_db()
        self.assertEqual(self.request_linked.status, AppointmentRequestStatus.REJECTED)
        self.assertEqual(self.request_linked.rejection_reason, "Doctor unavailable on preferred date.")

        self.assertTrue(PatientTimeline.objects.filter(patient=self.patient, event="Appointment Request Rejected").exists())

    def test_reschedule_request_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-reschedule", kwargs={"id": self.request_linked.id})
        data = {
            "doctor_id": str(self.doctor_user.id),
            "appointment_date": "2026-07-22",
            "start_time": "11:00",
            "reason": "Requested date slot full."
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.request_linked.refresh_from_db()
        self.assertEqual(self.request_linked.status, "RESCHEDULED")
        self.assertEqual(str(self.request_linked.preferred_date), "2026-07-22")
        self.assertEqual(self.request_linked.preferred_time_slot, "11:00")

    # ==========================================
    # 2. APPOINTMENT LIFE-CYCLE MANAGEMENT TESTS
    # ==========================================

    def test_appointment_lifecycle(self):
        # Create a confirmed appointment
        appt = Appointment.objects.create(
            appointment_number="APT-TEST-999",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        # 1. Check-In (Confirmed -> Checked In)
        self.client.force_authenticate(user=self.receptionist_user)
        url_checkin = reverse("appointment-check-in", kwargs={"id": appt.id})
        response = self.client.post(url_checkin)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.CHECKED_IN)
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=appt, event="Patient Checked In").exists())

        # 2. Start Consultation (Checked In -> In Consultation)
        # Must be authenticated as the assigned doctor
        self.client.force_authenticate(user=self.doctor_user)
        url_start = reverse("appointment-start-consultation", kwargs={"id": appt.id})
        response = self.client.post(url_start)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.IN_CONSULTATION)
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=appt, event="Consultation Started").exists())

    def test_edit_appointment_change_doctor_valid(self):
        appt = Appointment.objects.create(
            appointment_number="APT-TEST-888",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-detail", kwargs={"id": appt.id})
        data = {
            "doctor_id": str(self.doctor_user_2.id),
            "notes": "Updated notes"
        }
        response = self.client.patch(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        appt.refresh_from_db()
        self.assertEqual(appt.doctor, self.doctor_user_2)
        self.assertEqual(appt.visit_reason, "Updated notes")

    def test_reschedule_confirmed_appointment_success(self):
        appt = Appointment.objects.create(
            appointment_number="APT-TEST-777",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-reschedule", kwargs={"id": appt.id})
        data = {
            "appointment_date": "2026-07-25",
            "start_time": "14:00",
            "reason": "Parent requested change"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        appt.refresh_from_db()
        self.assertEqual(appt.appointment_date, datetime.date(2026, 7, 25))
        self.assertEqual(appt.start_time, datetime.time(14, 0))
        self.assertEqual(appt.status, AppointmentStatus.RESCHEDULED)

    def test_cancel_appointment_success(self):
        appt = Appointment.objects.create(
            appointment_number="APT-TEST-666",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-cancel", kwargs={"id": appt.id})
        data = {
            "reason": "Patient canceled."
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.CANCELLED)

    def test_mark_no_show_success(self):
        appt = Appointment.objects.create(
            appointment_number="APT-TEST-555",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-mark-no-show", kwargs={"id": appt.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        appt.refresh_from_db()
        self.assertEqual(appt.status, AppointmentStatus.NO_SHOW)
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=appt, event="Patient Did Not Attend").exists())

    # ==========================================
    # 3. PERMISSION VALIDATION TESTS
    # ==========================================

    def test_doctor_permission_restrictions(self):
        appt = Appointment.objects.create(
            appointment_number="APT-TEST-444",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date(2026, 7, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        # Doctor cannot cancel appointment
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("appointment-cancel", kwargs={"id": appt.id})
        response = self.client.post(url, {"reason": "Not allowed"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Doctor cannot reschedule appointment
        url_resched = reverse("appointment-reschedule", kwargs={"id": appt.id})
        response = self.client.post(url_resched, {"appointment_date": "2026-07-25", "start_time": "12:00"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Doctor can view appointment details
        url_detail = reverse("appointment-detail", kwargs={"id": appt.id})
        response = self.client.get(url_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
