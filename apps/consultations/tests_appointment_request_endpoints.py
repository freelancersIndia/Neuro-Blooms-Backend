import datetime
import io
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
    ClinicSettings,
    ClinicWeeklySchedule,
    DoctorAvailability,
    DoctorWorkingDay,
    ClinicHoliday,
    ClinicBreak
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

User = get_user_model()

class AppointmentRequestEndpointsTestCase(APITestCase):

    def setUp(self):
        # 1. Setup Roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # 2. Setup Users
        self.admin_user = User.objects.create_user(
            email="admin.req@test.com", password="password123", first_name="Admin"
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.receptionist_user = User.objects.create_user(
            email="receptionist.req@test.com", password="password123", first_name="Receptionist"
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.doctor_user = User.objects.create_user(
            email="doctor.req@test.com", password="password123", first_name="Doctor"
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Clear existing requests/patients/appointments
        AppointmentRequest.objects.all().delete()
        Patient.objects.all_with_deleted().delete()
        Appointment.objects.all().delete()
        ClinicSettings.objects.all().delete()
        ClinicWeeklySchedule.objects.all().delete()
        ClinicHoliday.objects.all().delete()
        ClinicBreak.objects.all().delete()

        # 3. Clinic Settings
        self.clinic_settings = ClinicSettings.objects.create(
            clinic_name="Neuro Blooms HQ",
            opening_time="09:00:00",
            closing_time="17:00:00",
            slot_duration_minutes=30,
            booking_window_days=30,
            allow_same_day_booking=True,
            max_daily_appointments=10,
            is_active=True
        )

        # 4. Weekly Schedules (open Monday-Friday)
        for wd in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]:
            ClinicWeeklySchedule.objects.create(
                weekday=wd,
                is_open=True,
                opening_time="09:00:00",
                closing_time="17:00:00"
            )

        # 5. Doctor Preferences and Working Days (Works Mon-Fri 09:00 to 17:00)
        self.doctor_availability = DoctorAvailability.objects.create(
            doctor=self.doctor_user,
            consultation_duration_minutes=30,
            max_daily_patients=5,
            accepts_appointments=True,
            is_active=True
        )

        for wd in [Weekday.MONDAY, Weekday.TUESDAY, Weekday.WEDNESDAY, Weekday.THURSDAY, Weekday.FRIDAY]:
            DoctorWorkingDay.objects.create(
                doctor=self.doctor_user,
                weekday=wd,
                is_working=True,
                start_time="09:00:00",
                end_time="17:00:00"
            )

        # 6. Seed Patients
        self.linked_patient = Patient.objects.create(
            patient_number="PAT-100001",
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

        # 7. Seed Requests
        # Request 1: Pending & Not Linked
        self.request_pending = AppointmentRequest.objects.create(
            request_number="REQ-2026-00001",
            parent_first_name="Sanjay",
            parent_last_name="Sharma",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9999988888",
            email="sanjay.sharma@test.com",
            child_first_name="Karan",
            child_last_name="Sharma",
            date_of_birth="2018-05-15",
            gender=Gender.MALE,
            appointment_type=AppointmentType.INITIAL,
            primary_concern="Speech delay concerns",
            preferred_date="2026-07-20", # A Monday
            preferred_time_slot="10:00 - 10:30",
            status=AppointmentRequestStatus.PENDING
        )

        # Request 2: Patient Linked (not approved yet)
        self.request_linked = AppointmentRequest.objects.create(
            request_number="REQ-2026-00002",
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
            primary_concern="Autism assessment review",
            preferred_date="2026-07-20",
            preferred_time_slot="11:00 - 11:30",
            status=AppointmentRequestStatus.PATIENT_LINKED,
            patient=self.linked_patient
        )

        # Request 3: Approved
        self.request_approved = AppointmentRequest.objects.create(
            request_number="REQ-2026-00003",
            parent_first_name="Deepa",
            parent_last_name="Patel",
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number="9888877777",
            email="deepa.patel@test.com",
            child_first_name="Dia",
            child_last_name="Patel",
            date_of_birth="2019-09-20",
            gender=Gender.FEMALE,
            appointment_type=AppointmentType.FOLLOW_UP,
            primary_concern="Follow-up speech assessment",
            preferred_date="2026-07-20",
            preferred_time_slot="14:00 - 14:30",
            status=AppointmentRequestStatus.APPROVED,
            patient=self.linked_patient
        )

    # ==========================================
    # API 1: STATISTICS ENDPOINT
    # ==========================================
    def test_statistics_endpoint_receptionist(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-statistics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertEqual(data["total_requests"], 3)
        self.assertEqual(data["pending"], 1)
        self.assertEqual(data["approved"], 1)
        self.assertEqual(data["linked_patient"], 2)
        self.assertEqual(data["not_linked"], 1)

    def test_statistics_endpoint_doctor_forbidden(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("appointment-request-statistics")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    # ==========================================
    # API 2: LISTING ENDPOINT
    # ==========================================
    def test_listing_endpoint_filters_and_metadata(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-list")
        
        # Test basic list
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 3)

        # Test action metadata on pending request (has no patient linked)
        pending_data = next(r for r in results if r["id"] == str(self.request_pending.id))
        self.assertFalse(pending_data["action_metadata"]["can_approve"])
        self.assertTrue(pending_data["action_metadata"]["can_link_patient"])
        self.assertTrue(pending_data["action_metadata"]["can_create_patient"])
        self.assertFalse(pending_data["action_metadata"]["can_convert"])

        # Test action metadata on patient linked request (ready for approval)
        linked_data = next(r for r in results if r["id"] == str(self.request_linked.id))
        self.assertTrue(linked_data["action_metadata"]["can_approve"])
        self.assertFalse(linked_data["action_metadata"]["can_link_patient"])
        self.assertFalse(linked_data["action_metadata"]["can_convert"])

        # Test filter status=PENDING
        response_pending = self.client.get(url, {"status": "PENDING"})
        self.assertEqual(response_pending.data["data"]["count"], 1)

        # Test search
        response_search = self.client.get(url, {"search": "Sharma"})
        self.assertEqual(response_search.data["data"]["count"], 1)

    # ==========================================
    # API 3: APPROVE REQUEST
    # ==========================================
    def test_approve_request_flow(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-approve", kwargs={"id": self.request_linked.id})
        response = self.client.post(url, {"notes": "Approved after verification"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        
        self.request_linked.refresh_from_db()
        self.assertEqual(self.request_linked.status, AppointmentRequestStatus.APPROVED)
        self.assertEqual(self.request_linked.reviewed_by, self.receptionist_user)
        self.assertIn("Approval Notes: Approved after verification", self.request_linked.additional_notes)

    def test_approve_request_errors(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Cannot approve approved request again
        url = reverse("appointment-request-approve", kwargs={"id": self.request_approved.id})
        response = self.client.post(url, {"notes": "Approved again"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # API 4: REJECT REQUEST
    # ==========================================
    def test_reject_request_flow(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-reject", kwargs={"id": self.request_pending.id})
        response = self.client.post(url, {"reason": "Outside clinic scope"}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.request_pending.refresh_from_db()
        self.assertEqual(self.request_pending.status, AppointmentRequestStatus.REJECTED)
        self.assertEqual(self.request_pending.rejection_reason, "Outside clinic scope")

    def test_reject_request_errors(self):
        self.client.force_authenticate(user=self.receptionist_user)
        # Reason is mandatory
        url = reverse("appointment-request-reject", kwargs={"id": self.request_pending.id})
        response = self.client.post(url, {"reason": ""}, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason", response.data["errors"])

    # ==========================================
    # API 5: LINK EXISTING PATIENT
    # ==========================================
    def test_link_existing_patient_flow(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-link-patient", kwargs={"id": self.request_pending.id})
        response = self.client.post(url, {"patient_id": str(self.linked_patient.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.request_pending.refresh_from_db()
        self.assertEqual(self.request_pending.patient, self.linked_patient)
        self.assertEqual(self.request_pending.status, AppointmentRequestStatus.PATIENT_LINKED)

    # ==========================================
    # API 6: CREATE PATIENT
    # ==========================================
    def test_create_patient_flow(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-create-patient", kwargs={"id": self.request_pending.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        
        self.request_pending.refresh_from_db()
        self.assertIsNotNone(self.request_pending.patient)
        self.assertEqual(self.request_pending.status, AppointmentRequestStatus.PATIENT_CREATED)
        self.assertTrue(self.request_pending.patient.patient_number.startswith("PAT-"))

    # ==========================================
    # API 7: CONVERT REQUEST TO APPOINTMENT
    # ==========================================
    def test_convert_to_appointment_flow(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-convert", kwargs={"id": self.request_approved.id})
        
        # Valid Slot: 2026-07-20 is a Monday (clinic open, doctor working)
        data = {
            "doctor": str(self.doctor_user.id),
            "appointment_date": "2026-07-20",
            "start_time": "14:00",
            "end_time": "14:30"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])

        # Re-convert should fail (already converted)
        response_dup = self.client.post(url, data, format="json")
        self.assertEqual(response_dup.status_code, status.HTTP_400_BAD_REQUEST)

    def test_convert_to_appointment_weekend_closed(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-convert", kwargs={"id": self.request_approved.id})
        # 2026-07-19 is a Sunday (clinic closed)
        data = {
            "doctor": str(self.doctor_user.id),
            "appointment_date": "2026-07-19",
            "start_time": "10:00",
            "end_time": "10:30"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # ==========================================
    # API 8: DOWNLOAD SUMMARY
    # ==========================================
    def test_download_summary_pdf(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-summary", kwargs={"id": self.request_pending.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn(b"%PDF", response.content)

    # ==========================================
    # API 9: FILTER METADATA OPTIONS
    # ==========================================
    def test_filter_metadata_options(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-filter-options")
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        data = response.data["data"]
        self.assertIn("statuses", data)
        self.assertIn("doctors", data)
        self.assertIn("appointment_types", data)
        self.assertIn("booking_sources", data)

    # ==========================================
    # API 10 & 11: BULK APPROVE & BULK REJECT
    # ==========================================
    def test_bulk_approve_partial_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-bulk-approve")
        
        # self.request_linked has a patient linked (approvable)
        # self.request_pending has no patient linked (should fail/skip)
        data = {
            "ids": [str(self.request_linked.id), str(self.request_pending.id)]
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res = response.data["data"]
        self.assertIn(str(self.request_linked.id), res["approved"])
        self.assertIn(str(self.request_pending.id), res["skipped"])
        self.assertIn(str(self.request_pending.id), res["errors"])

    def test_bulk_reject_partial_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-bulk-reject")
        
        data = {
            "ids": [str(self.request_linked.id), str(self.request_pending.id)],
            "reason": "Bulk cancel reason"
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        res = response.data["data"]
        self.assertIn(str(self.request_linked.id), res["rejected"])
        self.assertIn(str(self.request_pending.id), res["rejected"])

    # ==========================================
    # API 12: BULK EXPORT
    # ==========================================
    def test_export_formats(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("appointment-request-export")

        # Test CSV export
        response_csv = self.client.post(url, {"format": "CSV"}, format="json")
        self.assertEqual(response_csv.status_code, status.HTTP_200_OK)
        self.assertEqual(response_csv["Content-Type"], "text/csv")
        self.assertIn(b"Request Number,", response_csv.content)

        # Test Excel export
        response_xlsx = self.client.post(url, {"format": "Excel"}, format="json")
        self.assertEqual(response_xlsx.status_code, status.HTTP_200_OK)
        self.assertEqual(response_xlsx["Content-Type"], "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        # Test PDF export
        response_pdf = self.client.post(url, {"format": "PDF"}, format="json")
        self.assertEqual(response_pdf.status_code, status.HTTP_200_OK)
        self.assertEqual(response_pdf["Content-Type"], "application/pdf")
