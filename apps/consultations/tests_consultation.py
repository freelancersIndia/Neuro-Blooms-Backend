import datetime
import io
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APITestCase

from apps.consultations.models import (
    Appointment,
    AppointmentRequest,
    Patient,
    Consultation,
    ConsultationAttachment,
    ConsultationActivityLog,
    ConsultationAuditLog,
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
from apps.accounts.models import Role, UserRole
from apps.accounts.constants.roles import SystemRole
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class ConsultationTestCase(APITestCase):

    def setUp(self):
        # Setup Roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # Create users
        self.super_admin = User.objects.create_superuser(
            email="super@neuroblooms.com",
            password="password123",
            first_name="Super",
            last_name="Admin"
        )
        self.admin_user = User.objects.create_user(
            email="admin@neuroblooms.com",
            password="password123",
            first_name="Admin",
            last_name="User"
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.receptionist_user = User.objects.create_user(
            email="receptionist@neuroblooms.com",
            password="password123",
            first_name="Receptionist",
            last_name="User"
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.doctor_user = User.objects.create_user(
            email="doctor@neuroblooms.com",
            password="password123",
            first_name="John",
            last_name="Smith"
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        self.doctor_user_2 = User.objects.create_user(
            email="doctor2@neuroblooms.com",
            password="password123",
            first_name="Jane",
            last_name="Doe"
        )
        UserRole.objects.create(user=self.doctor_user_2, role=self.doctor_role)

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

        # Create Patient
        self.patient = Patient.objects.create(
            patient_number="PAT-000001",
            child_first_name="Jimmy",
            child_last_name="Doe",
            date_of_birth=datetime.date(2020, 5, 15),
            gender=Gender.MALE,
            parent_first_name="John",
            parent_last_name="Doe",
            mobile_number="9876543210",
            email="parent@example.com",
            relationship_to_child=RelationshipToChild.FATHER
        )

        # Create active appointment (Checked In)
        self.appointment = Appointment.objects.create(
            appointment_number="APT-000001",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.INITIAL,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.CHECKED_IN,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(10, 30),
            duration_minutes=30,
            visit_reason="Speech delay",
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

    def test_open_consultation_success(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-appointment-detail", kwargs={"appointment_id": self.appointment.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["success"], True)
        self.assertEqual(response.data["data"]["appointment"]["id"], str(self.appointment.id))
        self.assertEqual(response.data["data"]["patient_summary"]["patient_profile"]["child_first_name"], "Jimmy")

    def test_open_consultation_invalid_status(self):
        # Change status to CONFIRMED (not allowed to open consultation yet)
        self.appointment.status = AppointmentStatus.CONFIRMED
        self.appointment.save()

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-appointment-detail", kwargs={"appointment_id": self.appointment.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_open_consultation_wrong_doctor(self):
        # Authenticate as doctor 2 (not assigned)
        self.client.force_authenticate(user=self.doctor_user_2)
        url = reverse("consultation-appointment-detail", kwargs={"appointment_id": self.appointment.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_open_consultation_admin_allowed_read_only(self):
        self.client.force_authenticate(user=self.admin_user)
        url = reverse("consultation-appointment-detail", kwargs={"appointment_id": self.appointment.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_summary(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-patient-summary", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["patient_profile"]["child_first_name"], "Jimmy")
        self.assertIn("years", response.data["data"]["patient_profile"]["age"])

    def test_create_consultation_success(self):
        # Transition appointment to IN_CONSULTATION first
        self.appointment.status = AppointmentStatus.IN_CONSULTATION
        self.appointment.save()

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-create")
        payload = {
            "appointment_id": str(self.appointment.id),
            "chief_complaint": "Difficulty pronouncing words",
            "clinical_findings": "Mild phonological delay noted.",
            "diagnosis": "Speech Sound Disorder",
            "treatment_notes": "Recommend speech therapy twice a week.",
            "recommendations": "Practice reading aloud daily."
        }
        response = self.client.post(url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["data"]["chief_complaint"], "Difficulty pronouncing words")
        self.assertEqual(response.data["data"]["is_completed"], False)

        # Verify Timeline entries
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=self.appointment, event="Consultation Started").exists())
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=self.appointment, event="Clinical Notes Added").exists())
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=self.appointment, event="Diagnosis Recorded").exists())
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=self.appointment, event="Treatment Updated").exists())

        # Verify Activity Logs
        self.assertTrue(ActivityLog.objects.filter(action=ActivityType.CONSULTATION_CREATED).exists())
        self.assertTrue(ConsultationActivityLog.objects.filter(action=ActivityType.CONSULTATION_CREATED).exists())

    def test_create_consultation_duplicate_prevention(self):
        self.appointment.status = AppointmentStatus.IN_CONSULTATION
        self.appointment.save()

        # Create first consultation
        Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint 1"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-create")
        payload = {
            "appointment_id": str(self.appointment.id),
            "chief_complaint": "Complaint 2"
        }
        response = self.client.post(url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("appointment_id", response.data["errors"])

    def test_update_consultation_success(self):
        # Create an active consultation
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Original complaint",
            diagnosis="Original diagnosis"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-update", kwargs={"consultation_id": consultation.id})
        payload = {
            "chief_complaint": "Updated complaint",
            "diagnosis": "Updated diagnosis"
        }
        response = self.client.patch(url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["chief_complaint"], "Updated complaint")
        self.assertEqual(response.data["data"]["diagnosis"], "Updated diagnosis")

        # Verify Audit Logs
        self.assertEqual(ConsultationAuditLog.objects.filter(consultation=consultation, field_name="chief_complaint").count(), 1)
        audit_log = ConsultationAuditLog.objects.filter(consultation=consultation, field_name="chief_complaint").first()
        self.assertEqual(audit_log.old_value, "Original complaint")
        self.assertEqual(audit_log.new_value, "Updated complaint")

    def test_update_consultation_completed_fails(self):
        # Create a completed consultation
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Original complaint",
            is_completed=True
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-update", kwargs={"consultation_id": consultation.id})
        payload = {
            "chief_complaint": "Updated complaint"
        }
        response = self.client.patch(url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_attachments_valid(self):
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-attachment-list-upload", kwargs={"consultation_id": consultation.id})
        
        file1 = SimpleUploadedFile("report.pdf", b"pdf content", content_type="application/pdf")
        file2 = SimpleUploadedFile("image.png", b"png content", content_type="image/png")
        
        response = self.client.post(url, {"files": [file1, file2]}, format="multipart")
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data["data"]), 2)
        self.assertEqual(response.data["data"][0]["original_name"], "report.pdf")

        # Test listing attachments
        response_list = self.client.get(url)
        self.assertEqual(response_list.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response_list.data["data"]), 2)

    def test_upload_attachments_invalid_format_rejected(self):
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-attachment-list-upload", kwargs={"consultation_id": consultation.id})
        
        bad_file = SimpleUploadedFile("script.py", b"print('hello')", content_type="text/x-python")
        
        response = self.client.post(url, {"files": [bad_file]}, format="multipart")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upload_attachments_oversized_rejected(self):
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-attachment-list-upload", kwargs={"consultation_id": consultation.id})
        
        # Create a file slightly larger than 20MB
        oversized_data = b"0" * (20 * 1024 * 1024 + 100)
        large_file = SimpleUploadedFile("huge.pdf", oversized_data, content_type="application/pdf")
        
        response = self.client.post(url, {"files": [large_file]}, format="multipart")
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_attachment_soft(self):
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint"
        )
        attachment = ConsultationAttachment.objects.create(
            consultation=consultation,
            uploaded_by=self.doctor_user,
            file=SimpleUploadedFile("doc.pdf", b"content", content_type="application/pdf"),
            original_name="doc.pdf",
            file_size=7,
            mime_type="application/pdf"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-attachment-delete", kwargs={
            "consultation_id": consultation.id,
            "attachment_id": attachment.id
        })
        response = self.client.delete(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify soft delete
        attachment.refresh_from_db()
        self.assertEqual(attachment.is_active, False)

    def test_complete_consultation_success(self):
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint",
            clinical_findings="Findings",
            diagnosis="F80.0 Speech disorder",
            treatment_notes="Therapy sessions",
            recommendations="Practice daily"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-complete", kwargs={"consultation_id": consultation.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["is_completed"], True)

        # Verify appointment status transitioned to COMPLETED
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, AppointmentStatus.COMPLETED)

        # Verify Timeline
        self.assertTrue(AppointmentTimeline.objects.filter(appointment=self.appointment, event="Consultation Completed").exists())

    def test_complete_consultation_missing_required_fields_fails(self):
        # Missing diagnosis, treatment_notes, recommendations
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Complaint"
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-complete", kwargs={"consultation_id": consultation.id})
        response = self.client.post(url)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("diagnosis", response.data["errors"])

    def test_previous_consultations_history(self):
        # Create a completed consultation
        self.appointment.status = AppointmentStatus.IN_CONSULTATION
        self.appointment.save()
        consultation = Consultation.objects.create(
            appointment=self.appointment,
            doctor=self.doctor_user,
            chief_complaint="Speech delay",
            diagnosis="Developmental delay",
            treatment_notes="Therapy",
            recommendations="Exercises",
            is_completed=True
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-history", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertEqual(response.data["results"][0]["diagnosis"], "Developmental delay")

    def test_followup_history(self):
        # Create a follow-up appointment and completed consultation
        followup_appt = Appointment.objects.create(
            appointment_number="APT-000002",
            patient=self.patient,
            doctor=self.doctor_user,
            appointment_type=AppointmentType.FOLLOW_UP,
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.COMPLETED,
            appointment_date=datetime.date.today(),
            start_time=datetime.time(11, 0),
            end_time=datetime.time(11, 30),
            duration_minutes=30,
            approved_by=self.admin_user,
            created_by=self.admin_user
        )
        Consultation.objects.create(
            appointment=followup_appt,
            doctor=self.doctor_user,
            chief_complaint="Follow-up check",
            diagnosis="Improving",
            treatment_notes="Continue therapy",
            recommendations="Practice daily",
            is_completed=True
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse("consultation-followup-history", kwargs={"patient_id": self.patient.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(response.data["data"][0]["diagnosis"], "Improving")

    def test_role_permissions_receptionist_cannot_modify(self):
        # A receptionist tries to create a consultation (should fail)
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("consultation-create")
        payload = {
            "appointment_id": str(self.appointment.id),
            "chief_complaint": "Complaint"
        }
        response = self.client.post(url, payload)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
