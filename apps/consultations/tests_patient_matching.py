import datetime
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models.user import Role, UserRole
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.models import AppointmentRequest, Patient, Appointment
from apps.consultations.models.consultation import Consultation
from apps.consultations.choices import (
    AppointmentRequestStatus,
    PatientStatus,
    Gender,
    RelationshipToChild,
    AppointmentType,
    AppointmentStatus,
    BookingSource,
)
from apps.consultations.services.patient_matching_service import PatientMatchingService

User = get_user_model()

class PatientMatchingBaseTestCase(APITestCase):
    def setUp(self):
        # 1. Create Roles
        self.admin_role, _ = Role.objects.get_or_create(name='ADMIN')
        self.receptionist_role, _ = Role.objects.get_or_create(name='RECEPTIONIST')
        self.doctor_role, _ = Role.objects.get_or_create(name='DOCTOR')

        # 2. Create Users
        self.admin_user = User.objects.create_user(
            email='admin@nb.com', password='password123', first_name='Admin', last_name='User'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.receptionist_user = User.objects.create_user(
            email='receptionist@nb.com', password='password123', first_name='Recep', last_name='User'
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.doctor_user = User.objects.create_user(
            email='doctor@nb.com', password='password123', first_name='Doctor', last_name='User'
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # 3. Create requests
        self.approved_request = AppointmentRequest.objects.create(
            request_number='REQ-2026-000001',
            parent_first_name='John',
            parent_last_name='Doe',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',
            email='john.doe@example.com',
            child_first_name='Jimmy',
            child_last_name='Doe',
            date_of_birth=datetime.date(2020, 5, 15),
            gender=Gender.MALE,
            appointment_type=AppointmentType.INITIAL,
            primary_concern='Speech Delay',
            preferred_date=datetime.date(2026, 7, 10),
            preferred_time_slot='10:00 AM - 11:00 AM',
            status=AppointmentRequestStatus.APPROVED
        )

        self.pending_request = AppointmentRequest.objects.create(
            request_number='REQ-2026-000002',
            parent_first_name='Jane',
            parent_last_name='Smith',
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number='9876543211',
            email='jane.smith@example.com',
            child_first_name='Sarah',
            child_last_name='Smith',
            date_of_birth=datetime.date(2021, 6, 20),
            gender=Gender.FEMALE,
            appointment_type=AppointmentType.INITIAL,
            primary_concern='Autism Assessment',
            preferred_date=datetime.date(2026, 7, 11),
            preferred_time_slot='11:00 AM - 12:00 PM',
            status=AppointmentRequestStatus.PENDING
        )


class PatientMatchingAlgorithmTests(PatientMatchingBaseTestCase):
    def test_score_calculation_exact_match(self):
        # Create a patient matching all criteria
        patient = Patient.objects.create(
            patient_number='NBP-000001',
            parent_first_name='John',
            parent_last_name='Doe',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',
            email='john.doe@example.com',
            child_first_name='Jimmy',
            child_last_name='Doe',
            date_of_birth=datetime.date(2020, 5, 15),
            gender=Gender.MALE,
            address='123 Main St',
            patient_status=PatientStatus.ACTIVE
        )

        score = PatientMatchingService.calculate_matching_score(self.approved_request, patient)
        self.assertEqual(score, 100.0)
        self.assertEqual(PatientMatchingService.get_confidence_level(score), "Very High Match")

    def test_score_calculation_partial_matches(self):
        # 1. Matches mobile only (50%)
        p1 = Patient.objects.create(
            patient_number='NBP-000002',
            parent_first_name='Mark',
            parent_last_name='Twain',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',
            email='mark@example.com',
            child_first_name='Huck',
            child_last_name='Finn',
            date_of_birth=datetime.date(2015, 1, 1),
            gender=Gender.MALE,
            address='456 Mississippi Rd',
            patient_status=PatientStatus.ACTIVE
        )
        score1 = PatientMatchingService.calculate_matching_score(self.approved_request, p1)
        self.assertEqual(score1, 50.0)
        self.assertEqual(PatientMatchingService.get_confidence_level(score1), "Low Confidence")

        # 2. Matches child first name, DOB, and parent first name (10% + 20% + 5% = 35%)
        p2 = Patient.objects.create(
            patient_number='NBP-000003',
            parent_first_name='John',
            parent_last_name='Galt',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='1111111111',
            email='galt@example.com',
            child_first_name='Jimmy',
            child_last_name='Galt',
            date_of_birth=datetime.date(2020, 5, 15),
            gender=Gender.MALE,
            address='Valley',
            patient_status=PatientStatus.ACTIVE
        )
        score2 = PatientMatchingService.calculate_matching_score(self.approved_request, p2)
        self.assertEqual(score2, 35.0)

    def test_candidate_detection_sorting(self):
        # Create patients with varying match levels
        p_very_high = Patient.objects.create(
            patient_number='NBP-000004',
            parent_first_name='John',
            parent_last_name='Doe',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',  # 50%
            email='john.doe@example.com',
            child_first_name='Jimmy',  # 10%
            child_last_name='Doe',  # 10%
            date_of_birth=datetime.date(2020, 5, 15),  # 20%
            gender=Gender.MALE,
            address='Address',
            patient_status=PatientStatus.ACTIVE
        ) # score = 90 (no parent last name match? Parent last name is Doe, matches. Wait, score should be 100. Let's make parent name partially match: first name only)
        
        p_very_high.parent_last_name = 'Galt'
        p_very_high.save()
        # score = 50 (mobile) + 10 (first child) + 10 (last child) + 20 (dob) + 5 (parent first) = 95%

        p_possible = Patient.objects.create(
            patient_number='NBP-000005',
            parent_first_name='Will',
            parent_last_name='Doe',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='1111111111',
            email='will@example.com',
            child_first_name='Jimmy',  # 10%
            child_last_name='Doe',  # 10%
            date_of_birth=datetime.date(2020, 5, 15),  # 20%
            gender=Gender.MALE,
            address='Address',
            patient_status=PatientStatus.ACTIVE
        ) # score = 10 + 10 + 20 + 5 (parent last name Doe) = 45% (wait, let's make it 65% by matching parent name Doe [5], DOB [20], Child full name [20], parent first name John [5])
        p_possible.parent_first_name = 'John'
        p_possible.parent_last_name = 'Doe'
        p_possible.save()
        # score = 20 (child full) + 20 (dob) + 10 (parent full) = 50%
        # Let's match mobile instead to make it 60%+
        p_possible.mobile_number = '9876543210' # mobile matches (50%) + child first (10%) + DOB (20%) = 80%

        p_possible.mobile_number = '9876543210'
        p_possible.child_first_name = 'Will'
        p_possible.child_last_name = 'Smith'
        p_possible.date_of_birth = datetime.date(2010, 1, 1)
        p_possible.parent_first_name = 'Alice'
        p_possible.parent_last_name = 'Smith'
        p_possible.save()
        # score = 50% (mobile match only)

        candidates = PatientMatchingService.get_duplicate_candidates(self.approved_request)
        self.assertEqual(candidates[0]["patient"].patient_number, p_very_high.patient_number)
        self.assertTrue(candidates[0]["score"] > candidates[1]["score"])


class PatientMatchingAPITests(PatientMatchingBaseTestCase):
    def test_screen_permissions(self):
        url = reverse('patient_matching_screen', kwargs={'appointment_request_id': self.approved_request.id})

        # Anonymous gets 401
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Doctor gets 403
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Receptionist gets 200
        self.client.force_authenticate(user=self.receptionist_role.users.first() or self.receptionist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_screen_data_validations(self):
        self.client.force_authenticate(user=self.receptionist_user)

        # Pending requests should fail (only APPROVED)
        url_pending = reverse('patient_matching_screen', kwargs={'appointment_request_id': self.pending_request.id})
        response = self.client.get(url_pending)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

        # Invalid UUID format should fail with 400
        url_invalid = reverse('patient_matching_screen', kwargs={'appointment_request_id': 'not-a-uuid'})
        response = self.client.get(url_invalid)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data["success"])

    def test_screen_data_returns_candidates(self):
        patient = Patient.objects.create(
            patient_number='NBP-000006',
            parent_first_name='John',
            parent_last_name='Doe',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',
            email='john.doe@example.com',
            child_first_name='Jimmy',
            child_last_name='Doe',
            date_of_birth=datetime.date(2020, 5, 15),
            gender=Gender.MALE,
            address='Address',
            patient_status=PatientStatus.ACTIVE
        )

        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patient_matching_screen', kwargs={'appointment_request_id': self.approved_request.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data["data"]
        self.assertEqual(data["best_match_score"], 100.0)
        self.assertEqual(len(data["matching_patients"]), 1)
        self.assertEqual(data["matching_patients"][0]["patient"]["patient_number"], patient.patient_number)
        
        # Verify activity log
        log_exists = ActivityLog.objects.filter(
            action=ActivityType.PATIENT_MATCHING_STARTED,
            description__icontains=self.approved_request.request_number
        ).exists()
        self.assertTrue(log_exists)


class PatientSearchTests(PatientMatchingBaseTestCase):
    def setUp(self):
        super().setUp()
        # Create test patients
        self.p1 = Patient.objects.create(
            patient_number='NBP-000010',
            parent_first_name='Alice',
            parent_last_name='Brown',
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number='1234567890',
            email='alice@brown.com',
            child_first_name='Charlie',
            child_last_name='Brown',
            date_of_birth=datetime.date(2018, 2, 10),
            gender=Gender.MALE,
            address='Brown House',
            patient_status=PatientStatus.ACTIVE
        )
        self.p2 = Patient.objects.create(
            patient_number='NBP-000011',
            parent_first_name='David',
            parent_last_name='Miller',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='0987654321',
            email='david@miller.com',
            child_first_name='Daisy',
            child_last_name='Miller',
            date_of_birth=datetime.date(2019, 3, 11),
            gender=Gender.FEMALE,
            address='Miller House',
            patient_status=PatientStatus.INACTIVE
        )

    def test_search_permissions(self):
        url = reverse('patient_manual_search')

        # Anon -> 401
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Doctor -> 200 (Read Only access)
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_search_filters_and_ordering(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patient_manual_search')

        # 1. Search by Child Name (case insensitive, whitespace tolerant)
        response = self.client.get(url, {'search': '  charlie brown  ', 'search_type': 'CHILD_NAME'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["patient_number"], self.p1.patient_number)

        # 2. Search by Parent Name
        response = self.client.get(url, {'search': 'david', 'search_type': 'PARENT_NAME'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["patient_number"], self.p2.patient_number)

        # 3. Search by Phone
        response = self.client.get(url, {'search': '123456', 'search_type': 'PHONE'})
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)

        # 4. Search by Email
        response = self.client.get(url, {'search': 'miller.com', 'search_type': 'EMAIL'})
        results = response.data["data"]["results"]
        self.assertEqual(len(results), 1)

        # Ordering by patient_id descending
        response = self.client.get(url, {'ordering': '-patient_id'})
        results = response.data["data"]["results"]
        self.assertEqual(results[0]["patient_number"], 'NBP-000011')
        self.assertEqual(results[1]["patient_number"], 'NBP-000010')


class PatientLinkTests(PatientMatchingBaseTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            patient_number='NBP-000020',
            parent_first_name='Jack',
            parent_last_name='Black',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',
            email='jack@black.com',
            child_first_name='Bobby',
            child_last_name='Black',
            date_of_birth=datetime.date(2017, 8, 12),
            gender=Gender.MALE,
            address='Rock Town',
            patient_status=PatientStatus.ACTIVE
        )

    def test_link_permissions(self):
        url = reverse('patient_matching_link', kwargs={'appointment_request_id': self.approved_request.id})

        # Doctor -> 403 Forbidden
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.post(url, {"patient_id": self.patient.patient_number})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Receptionist -> 200 OK
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.post(url, {"patient_id": self.patient.patient_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_link_logic_and_activity_logs(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patient_matching_link', kwargs={'appointment_request_id': self.approved_request.id})

        # Perform link
        response = self.client.post(url, {"patient_id": self.patient.patient_number})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["success"])

        # Check request status
        self.approved_request.refresh_from_db()
        self.assertEqual(self.approved_request.status, AppointmentRequestStatus.PATIENT_LINKED)
        self.assertEqual(self.approved_request.patient, self.patient)
        self.assertEqual(self.approved_request.patient_linked_by, self.receptionist_user)
        self.assertIsNotNone(self.approved_request.patient_linked_at)

        # Check ActivityLog
        log = ActivityLog.objects.filter(action=ActivityType.PATIENT_LINKED).first()
        self.assertIsNotNone(log)
        self.assertIn(self.approved_request.request_number, log.description)
        self.assertIn(self.patient.patient_number, log.description)

        # Try to link again (should fail)
        response2 = self.client.post(url, {"patient_id": self.patient.patient_number})
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)


class PatientCreateTests(PatientMatchingBaseTestCase):
    def test_create_patient_from_request(self):
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patient_matching_create_patient', kwargs={'appointment_request_id': self.approved_request.id})

        # Run creation API
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data["success"])
        
        # Verify created patient number format
        patient_id = response.data["data"]["patient_id"]
        self.assertEqual(patient_id, 'NBP-000001')

        # Verify database record
        patient = Patient.objects.get(patient_number=patient_id)
        self.assertEqual(patient.child_first_name, self.approved_request.child_first_name)
        self.assertEqual(patient.parent_first_name, self.approved_request.parent_first_name)
        self.assertEqual(patient.mobile_number, self.approved_request.mobile_number)
        
        # Verify request status update
        self.approved_request.refresh_from_db()
        self.assertEqual(self.approved_request.status, AppointmentRequestStatus.PATIENT_CREATED)
        self.assertEqual(self.approved_request.patient, patient)
        self.assertEqual(self.approved_request.patient_created_by, self.receptionist_user)
        self.assertIsNotNone(self.approved_request.patient_created_at)

        # Verify activity log
        log = ActivityLog.objects.filter(action=ActivityType.PATIENT_CREATED).first()
        self.assertIsNotNone(log)

        # Check next sequential number generation
        req_2 = AppointmentRequest.objects.create(
            request_number='REQ-2026-000003',
            parent_first_name='Will',
            parent_last_name='Smith',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543299',
            email='will.smith@example.com',
            child_first_name='Jaden',
            child_last_name='Smith',
            date_of_birth=datetime.date(2018, 9, 8),
            gender=Gender.MALE,
            appointment_type=AppointmentType.INITIAL,
            primary_concern='Speech Delay',
            preferred_date=datetime.date(2026, 7, 12),
            preferred_time_slot='10:00 AM - 11:00 AM',
            status=AppointmentRequestStatus.APPROVED
        )
        url2 = reverse('patient_matching_create_patient', kwargs={'appointment_request_id': req_2.id})
        response2 = self.client.post(url2)
        self.assertEqual(response2.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response2.data["data"]["patient_id"], 'NBP-000002')


class PatientPreviewTests(PatientMatchingBaseTestCase):
    def setUp(self):
        super().setUp()
        self.patient = Patient.objects.create(
            patient_number='NBP-000030',
            parent_first_name='Leo',
            parent_last_name='Messi',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='1010101010',
            email='messi@barca.com',
            child_first_name='Thiago',
            child_last_name='Messi',
            date_of_birth=datetime.date(2012, 11, 2),
            gender=Gender.MALE,
            address='Barcelona',
            patient_status=PatientStatus.ACTIVE
        )

        # Create appointment and completed consultation
        self.appt = Appointment.objects.create(
            appointment_number='APT-000001',
            patient=self.patient,
            appointment_request=self.approved_request,
            appointment_type=AppointmentType.FOLLOW_UP, # followup
            booking_source=BookingSource.RECEPTIONIST,
            status=AppointmentStatus.COMPLETED,
            appointment_date=datetime.date(2026, 6, 20),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            reason_for_visit='Followup visit',
            approved_by=self.admin_user,
            created_by=self.admin_user
        )

        self.consult = Consultation.objects.create(
            appointment=self.appt,
            doctor=self.doctor_user,
            consultation_summary='Summary',
            clinical_observation='Observation',
            doctor_recommendations='Recs',
            followup_required=True
        )

    def test_preview_data(self):
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patient_preview', kwargs={'patient_id': self.patient.patient_number})

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data["data"]
        self.assertEqual(data["patient_id"], self.patient.patient_number)
        self.assertEqual(data["appointments_count"], 1)
        self.assertEqual(data["consultations_count"], 1)
        self.assertEqual(data["followups_count"], 1)
        self.assertEqual(data["last_visit"], '2026-06-20')
        self.assertEqual(data["age"], datetime.date.today().year - 2012 - ((datetime.date.today().month, datetime.date.today().day) < (11, 2)))

        # Try to access using invalid patient number (returns 404)
        url_404 = reverse('patient_preview', kwargs={'patient_id': 'NBP-999999'})
        response_404 = self.client.get(url_404)
        self.assertEqual(response_404.status_code, status.HTTP_404_NOT_FOUND)
