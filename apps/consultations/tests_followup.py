import datetime
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from apps.consultations.models import (
    Appointment,
    Patient,
    Consultation,
    TreatmentCase,
    AppointmentTimeline,
    PatientTimeline,
    ConsultationAuditLog,
    ClinicSettings,
    ClinicWeeklySchedule,
    DoctorAvailability,
    DoctorWorkingDay
)
from apps.consultations.models.treatment_case import TreatmentCaseStatus
from apps.consultations.choices import AppointmentStatus, AppointmentType, BookingSource, Priority, Weekday
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.models import Role, UserRole
from apps.accounts.constants.roles import SystemRole

User = get_user_model()

class FollowupTestCase(APITestCase):

    def setUp(self):
        # Setup Roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # Create Users
        self.doctor_user = User.objects.create_user(
            email="doctor@neuroblooms.com",
            password="Password123",
            first_name="John",
            last_name="Smith"
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        self.receptionist_user = User.objects.create_user(
            email="receptionist@neuroblooms.com",
            password="Password123",
            first_name="Jane",
            last_name="Doe"
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.admin_user = User.objects.create_user(
            email="admin@neuroblooms.com",
            password="Password123",
            first_name="Admin",
            last_name="User"
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        # Setup Clinic Settings & Weekly Schedule
        self.clinic_settings = ClinicSettings.objects.create(
            clinic_name="Neuro Blooms",
            opening_time="09:00:00",
            closing_time="17:00:00",
            slot_duration_minutes=30,
            booking_window_days=30,
            allow_same_day_booking=True,
            max_daily_appointments=50,
            timezone="Asia/Kolkata"
        )
        for wd in Weekday.values:
            ClinicWeeklySchedule.objects.create(
                weekday=wd,
                is_open=True,
                opening_time="09:00:00",
                closing_time="17:00:00"
            )

        # Setup Doctor Availability & Working Days
        DoctorAvailability.objects.create(
            doctor=self.doctor_user,
            accepts_appointments=True,
            consultation_duration_minutes=30,
            max_daily_patients=10
        )
        for wd in Weekday.values:
            DoctorWorkingDay.objects.create(
                doctor=self.doctor_user,
                weekday=wd,
                is_working=True,
                start_time="09:00:00",
                end_time="17:00:00"
            )

        # Create Patient
        self.patient = Patient.objects.create(
            patient_number="PAT-000001",
            child_first_name="Tommy",
            child_last_name="Helper",
            date_of_birth=datetime.date(2020, 5, 12),
            gender="MALE",
            parent_first_name="Peter",
            parent_last_name="Helper",
            mobile_number="9876543210",
            email="peter@helper.com",
            is_active=True
        )

        # Create an initial appointment in IN_CONSULTATION status
        self.appointment = Appointment.objects.create(
            appointment_number="APT-000001",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.COMPLETED,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            duration_minutes=30,
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        # Create a completed consultation
        self.consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Speech delay",
            diagnosis="Developmental speech delay",
            treatment_notes="Speech therapy recommended",
            is_completed=True
        )

        # The TreatmentCase should be automatically created and linked in the save/create flow
        # But we will ensure it is set up correctly in our tests
        self.treatment_case = TreatmentCase.objects.create(
            patient=self.patient,
            doctor=self.doctor_user,
            status=TreatmentCaseStatus.ACTIVE,
            primary_diagnosis="Developmental speech delay"
        )
        self.consultation.treatment_case = self.treatment_case
        self.consultation.save()
        self.appointment.treatment_case = self.treatment_case
        self.appointment.save()

    # ==========================================
    # 1. FOLLOW-UP DECISION ENDPOINT
    # ==========================================

    def test_followup_decision_requires_followup_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-followup-decision", kwargs={"consultation_id": self.consultation.id})
        payload = {"requires_followup": True}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Ready to create follow-up.")

        # Verify treatment case status
        self.treatment_case.refresh_from_db()
        self.assertEqual(self.treatment_case.status, TreatmentCaseStatus.FOLLOW_UP_REQUIRED)

        # Verify timelines
        self.assertTrue(PatientTimeline.objects.filter(patient=self.patient, event="Follow-up Required").exists())

    def test_followup_decision_treatment_complete_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-followup-decision", kwargs={"consultation_id": self.consultation.id})
        payload = {"requires_followup": False}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["message"], "Case Closed.")

        # Verify treatment case status
        self.treatment_case.refresh_from_db()
        self.assertEqual(self.treatment_case.status, TreatmentCaseStatus.CASE_CLOSED)
        self.assertIsNotNone(self.treatment_case.end_date)

        # Verify timelines
        self.assertTrue(PatientTimeline.objects.filter(patient=self.patient, event="Treatment Completed").exists())

    def test_followup_decision_cannot_execute_twice(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-followup-decision", kwargs={"consultation_id": self.consultation.id})
        payload = {"requires_followup": True}
        
        # Record first time
        self.client.post(url, payload)

        # Record second time
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("requires_followup", response.data["errors"])

    # ==========================================
    # 2. CREATE FOLLOW-UP ENDPOINT
    # ==========================================

    def test_create_followup_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("followup-create")
        
        # We need a future date that is a weekday for the clinic. Let's use next Monday.
        today = datetime.date.today()
        next_monday = today + datetime.timedelta(days=(7 - today.weekday()))
        
        payload = {
            "consultation_id": str(self.consultation.id),
            "doctor_id": str(self.doctor_user.id),
            "followup_date": next_monday.strftime("%Y-%m-%d"),
            "start_time": "11:00",
            "reason": "Follow-up speech assessment",
            "notes": "Bring worksheets"
        }
        
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        self.assertEqual(response.data["data"]["status"], AppointmentStatus.CONFIRMED)
        self.assertEqual(response.data["data"]["appointment_type"], AppointmentType.FOLLOW_UP)

        # Verify treatment case status
        self.treatment_case.refresh_from_db()
        self.assertEqual(self.treatment_case.status, TreatmentCaseStatus.FOLLOW_UP_SCHEDULED)

        # Verify timeline
        self.assertTrue(PatientTimeline.objects.filter(patient=self.patient, event="Follow-up Created").exists())

    def test_create_followup_after_case_closed_fails(self):
        # Close the treatment case
        self.treatment_case.status = TreatmentCaseStatus.CASE_CLOSED
        self.treatment_case.save()

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("followup-create")
        
        today = datetime.date.today()
        next_monday = today + datetime.timedelta(days=(7 - today.weekday()))
        
        payload = {
            "consultation_id": str(self.consultation.id),
            "doctor_id": str(self.doctor_user.id),
            "followup_date": next_monday.strftime("%Y-%m-%d"),
            "start_time": "11:00",
            "reason": "Follow-up speech assessment"
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("treatment_case", response.data["errors"])

    def test_create_followup_duplicate_fails(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("followup-create")
        
        today = datetime.date.today()
        next_monday = today + datetime.timedelta(days=(7 - today.weekday()))
        
        payload = {
            "consultation_id": str(self.consultation.id),
            "doctor_id": str(self.doctor_user.id),
            "followup_date": next_monday.strftime("%Y-%m-%d"),
            "start_time": "11:00",
            "reason": "Follow-up speech assessment"
        }
        
        # First creation
        response1 = self.client.post(url, payload)
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second creation from same consultation
        payload["start_time"] = "11:30"  # different slot to avoid slot conflict
        response2 = self.client.post(url, payload)
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("consultation_id", response2.data["errors"])

    # ==========================================
    # 3. GET FOLLOW-UP DETAILS ENDPOINT
    # ==========================================

    def test_get_followup_details_success(self):
        # Create a follow-up appointment
        followup = Appointment.objects.create(
            appointment_number="APT-000002",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.FOLLOW_UP,
            booking_source=BookingSource.ADMIN_PANEL,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(11, 30),
            duration_minutes=30,
            previous_consultation=self.consultation,
            treatment_case=self.treatment_case,
            approved_by=self.admin_user,
            created_by=self.doctor_user
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("followup-detail", kwargs={"appointment_id": followup.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["previous_diagnosis"], "Developmental speech delay")

    # ==========================================
    # 4. UPDATE FOLLOW-UP ENDPOINT
    # ==========================================

    def test_update_followup_success(self):
        followup = Appointment.objects.create(
            appointment_number="APT-000002",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.FOLLOW_UP,
            booking_source=BookingSource.ADMIN_PANEL,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date.today() + datetime.timedelta(days=1),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(11, 30),
            duration_minutes=30,
            previous_consultation=self.consultation,
            treatment_case=self.treatment_case,
            approved_by=self.admin_user,
            created_by=self.doctor_user
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("followup-detail", kwargs={"appointment_id": followup.id})
        
        today = datetime.date.today()
        next_tuesday = today + datetime.timedelta(days=(8 - today.weekday()))
        
        payload = {
            "appointment_date": next_tuesday.strftime("%Y-%m-%d"),
            "start_time": "12:00",
            "reason": "Updated reason",
            "notes": "Updated notes"
        }
        response = self.client.patch(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        followup.refresh_from_db()
        self.assertEqual(followup.appointment_date, next_tuesday)
        self.assertEqual(followup.start_time, datetime.time(12, 0))
        self.assertEqual(followup.visit_reason, "Updated reason")

        # Verify audit logs
        self.assertTrue(ConsultationAuditLog.objects.filter(field_name="visit_reason", new_value="Updated reason").exists())

    # ==========================================
    # 5. CANCEL FOLLOW-UP ENDPOINT
    # ==========================================

    def test_cancel_followup_success(self):
        followup = Appointment.objects.create(
            appointment_number="APT-000002",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.FOLLOW_UP,
            booking_source=BookingSource.ADMIN_PANEL,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(11, 30),
            duration_minutes=30,
            previous_consultation=self.consultation,
            treatment_case=self.treatment_case,
            approved_by=self.admin_user,
            created_by=self.doctor_user
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("followup-cancel", kwargs={"appointment_id": followup.id})
        payload = {"reason": "Patient has a school exam."}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        followup.refresh_from_db()
        self.assertEqual(followup.status, AppointmentStatus.CANCELLED)

        # Verify treatment case status reverts to FOLLOW_UP_REQUIRED
        self.treatment_case.refresh_from_db()
        self.assertEqual(self.treatment_case.status, TreatmentCaseStatus.FOLLOW_UP_REQUIRED)

    # ==========================================
    # 6. TREATMENT CASE JOURNEY ENDPOINT
    # ==========================================

    def test_get_treatment_case_journey_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("treatment-case-detail", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["status"], TreatmentCaseStatus.ACTIVE)
        self.assertEqual(len(response.data["data"]["consultations"]), 1)

    # ==========================================
    # 7. CLOSE TREATMENT CASE ENDPOINT
    # ==========================================

    def test_close_treatment_case_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("treatment-case-close", kwargs={"patient_id": self.patient.id})
        payload = {
            "closing_summary": "Tommy shows significant improvement in phonetic articulation.",
            "outcome": "Treatment Completed"
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.treatment_case.refresh_from_db()
        self.assertEqual(self.treatment_case.status, TreatmentCaseStatus.CASE_CLOSED)
        self.assertEqual(self.treatment_case.closing_summary, "Tommy shows significant improvement in phonetic articulation.")

    def test_close_treatment_case_pending_appointment_fails(self):
        # Create a future confirmed appointment
        Appointment.objects.create(
            appointment_number="APT-000002",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.FOLLOW_UP,
            booking_source=BookingSource.ADMIN_PANEL,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=datetime.date.today() + datetime.timedelta(days=2),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(11, 30),
            duration_minutes=30,
            previous_consultation=self.consultation,
            treatment_case=self.treatment_case,
            approved_by=self.admin_user,
            created_by=self.doctor_user
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("treatment-case-close", kwargs={"patient_id": self.patient.id})
        payload = {
            "closing_summary": "Articulatory targets met.",
            "outcome": "Treatment Completed"
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("patient_id", response.data["errors"])

    # ==========================================
    # 8. REOPEN TREATMENT CASE ENDPOINT
    # ==========================================

    def test_reopen_treatment_case_success(self):
        # First close it
        self.treatment_case.status = TreatmentCaseStatus.CASE_CLOSED
        self.treatment_case.end_date = datetime.date.today()
        self.treatment_case.save()

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("treatment-case-reopen", kwargs={"patient_id": self.patient.id})
        payload = {"reason": "Mild regression noticed after school holidays."}
        response = self.client.post(url, payload)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.treatment_case.refresh_from_db()
        self.assertEqual(self.treatment_case.status, TreatmentCaseStatus.ACTIVE)
        self.assertEqual(self.treatment_case.reopen_reason, "Mild regression noticed after school holidays.")

    # ==========================================
    # 9. ROLE PERMISSIONS
    # ==========================================

    def test_receptionist_permissions_restricted(self):
        self.client.force_authenticate(user=self.receptionist_user)
        
        # 1. Re-recording follow-up decision (Write) -> Should fail
        url_decision = reverse("consultation-followup-decision", kwargs={"consultation_id": self.consultation.id})
        response_decision = self.client.post(url_decision, {"requires_followup": True})
        self.assertEqual(response_decision.status_code, status.HTTP_403_FORBIDDEN)

        # 2. Creating follow-up (Write) -> Should fail
        url_create = reverse("followup-create")
        response_create = self.client.post(url_create, {})
        self.assertEqual(response_create.status_code, status.HTTP_403_FORBIDDEN)

        # 3. Viewing treatment case (Read-only) -> Should succeed
        url_journey = reverse("treatment-case-detail", kwargs={"patient_id": self.patient.id})
        response_journey = self.client.get(url_journey)
        self.assertEqual(response_journey.status_code, status.HTTP_200_OK)
