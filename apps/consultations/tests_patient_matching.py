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
    PatientTimeline
)
from apps.consultations.choices import (
    Gender,
    RelationshipToChild,
    AppointmentRequestStatus,
    AppointmentType
)
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class PatientMatchingTestCase(APITestCase):

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

        # Clean DB
        AppointmentRequest.objects.all().delete()
        Patient.objects.all_with_deleted().delete()
        PatientTimeline.objects.all().delete()
        ActivityLog.objects.all().delete()

        # Create some baseline patients for matching
        self.patient_exact = Patient.objects.create(
            patient_number="PAT-000001",
            parent_first_name="Ravi",
            parent_last_name="Kumar",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9876543210",
            email="ravi.kumar@test.com",
            child_first_name="Aarav",
            child_last_name="Kumar",
            date_of_birth="2020-01-01",
            gender=Gender.MALE,
            address="123 Street"
        )

        self.patient_high = Patient.objects.create(
            patient_number="PAT-000002",
            parent_first_name="Ravi",
            parent_last_name="Sharma",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9876543210", # Same mobile (50)
            email="ravi.sharma@test.com",
            child_first_name="Aarav", # Same child first name (10)
            child_last_name="Sharma",
            date_of_birth="2020-01-01", # Same DOB (10)
            gender=Gender.MALE, # Same Gender (5)
            address="456 Lane"
        ) # Parent First Name is Ravi (7.5) -> Total = 82.5 (High Probability)

        self.patient_possible = Patient.objects.create(
            patient_number="PAT-000003",
            parent_first_name="Sanjay",
            parent_last_name="Gupta",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9876543210", # Same mobile (50)
            email="sanjay@test.com",
            child_first_name="Siddharth", # Different child name
            child_last_name="Gupta",
            date_of_birth="2020-01-01", # Same DOB (10)
            gender=Gender.MALE, # Same Gender (5)
            address="789 Blvd"
        ) # Total = 65 (Possible Match)

        # Create an Appointment Request that matches patient_exact perfectly
        self.request_exact = AppointmentRequest.objects.create(
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
            status=AppointmentRequestStatus.PENDING
        )

    # ==========================================
    # 1. PATIENT MATCHING ALGORITHM TESTS
    # ==========================================

    def test_patient_matching_exact(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("patient-matching")
        response = self.client.get(url, {"request_id": str(self.request_exact.id)})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["total_matches"], 3)
        
        # Verify first match is exact match (95% - 100%)
        best_match = response.data["data"]["matches"][0]
        self.assertEqual(best_match["patient_code"], "PAT-000001")
        self.assertEqual(best_match["match_level"], "EXACT_MATCH")
        self.assertEqual(best_match["match_score"], 100)
        self.assertIn("mobile_number", best_match["matched_fields"])
        self.assertIn("child_name", best_match["matched_fields"])
        self.assertIn("date_of_birth", best_match["matched_fields"])

    def test_patient_matching_high_probability(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("patient-matching")
        response = self.client.get(url, {"request_id": str(self.request_exact.id)})

        matches = response.data["data"]["matches"]
        
        high_match = next((m for m in matches if m["patient_code"] == "PAT-000002"), None)
        self.assertIsNotNone(high_match)
        self.assertEqual(high_match["match_level"], "HIGH_PROBABILITY")

        possible_match = next((m for m in matches if m["patient_code"] == "PAT-000003"), None)
        self.assertIsNotNone(possible_match)
        self.assertEqual(possible_match["match_level"], "POSSIBLE_MATCH")

    # ==========================================
    # 2. MANUAL SEARCH TESTS
    # ==========================================

    def test_manual_search_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("patient-search")
        
        # Search by child name
        response = self.client.get(url, {"search": "Aarav"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 2) # Aarav Kumar and Aarav Sharma

        # Search by mobile number
        response = self.client.get(url, {"search": "987654"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"]["count"], 3)

    def test_manual_search_validation_min_length(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("patient-search")
        response = self.client.get(url, {"search": "A"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("search", response.data["errors"])

    # ==========================================
    # 3. PATIENT LINKING TESTS
    # ==========================================

    def test_link_patient_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("patient-link")
        data = {
            "request_id": str(self.request_exact.id),
            "patient_id": str(self.patient_exact.id)
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify request status updated
        self.request_exact.refresh_from_db()
        self.assertEqual(self.request_exact.status, AppointmentRequestStatus.PATIENT_LINKED)
        self.assertEqual(self.request_exact.patient, self.patient_exact)

        # Verify timeline entries
        timeline_events = PatientTimeline.objects.filter(patient=self.patient_exact)
        self.assertEqual(timeline_events.count(), 2)
        self.assertEqual(timeline_events[0].event, "Patient Matching Started")
        self.assertEqual(timeline_events[1].event, "Patient Linked")

        # Verify activity log
        log_exists = ActivityLog.objects.filter(action=ActivityType.PATIENT_LINKED, user=self.receptionist_user).exists()
        self.assertTrue(log_exists)

    # ==========================================
    # 4. CREATE PATIENT TESTS
    # ==========================================

    def test_create_patient_success(self):
        self.client.force_authenticate(user=self.receptionist_user)
        
        # To make creation succeed without exact match error, let's create a request that has NO matches
        request_unique = AppointmentRequest.objects.create(
            request_number="REQ-2026-00002",
            parent_first_name="John",
            parent_last_name="Doe",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="1111111111",
            email="john@test.com",
            child_first_name="Johnny",
            child_last_name="Doe",
            date_of_birth="2022-02-02",
            gender=Gender.MALE,
            appointment_type=AppointmentType.INITIAL,
            primary_concern="Sensory integration",
            preferred_date="2026-07-20",
            preferred_time_slot="11:00 - 11:30",
            status=AppointmentRequestStatus.PENDING
        )

        url = reverse("patient-create-patient")
        data = {
            "request_id": str(request_unique.id)
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        
        patient_id = response.data["data"]["id"]
        patient = Patient.objects.get(id=patient_id)
        self.assertEqual(patient.child_first_name, "Johnny")
        self.assertEqual(patient.patient_number, "PAT-000004") # Next code

        # Verify request linked and status updated
        request_unique.refresh_from_db()
        self.assertEqual(request_unique.status, AppointmentRequestStatus.PATIENT_CREATED)
        self.assertEqual(request_unique.patient, patient)

        # Verify timeline
        timeline_events = PatientTimeline.objects.filter(patient=patient)
        self.assertEqual(timeline_events.count(), 2)
        self.assertEqual(timeline_events[0].event, "Patient Matching Started")
        self.assertEqual(timeline_events[1].event, "New Patient Created")

    def test_create_patient_prevent_duplicate(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse("patient-create-patient")
        # Try creating patient from request_exact (which matches self.patient_exact 100%)
        data = {
            "request_id": str(self.request_exact.id)
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("non_field_errors", response.data["errors"])
        self.assertIn("already exists in the system", response.data["errors"]["non_field_errors"][0])

    # ==========================================
    # 5. PERMISSION TESTS
    # ==========================================

    def test_patient_matching_permissions(self):
        # 1. Doctor (Read Only - can view matching, cannot link/create)
        self.client.force_authenticate(user=self.doctor_user)
        
        url_match = reverse("patient-matching")
        response = self.client.get(url_match, {"request_id": str(self.request_exact.id)})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url_link = reverse("patient-link")
        response = self.client.post(url_link, {"request_id": str(self.request_exact.id), "patient_id": str(self.patient_exact.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        url_create = reverse("patient-create-patient")
        response = self.client.post(url_create, {"request_id": str(self.request_exact.id)}, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
