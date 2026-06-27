import datetime
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.accounts.models.user import Role, UserRole
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.models import Patient, Appointment
from apps.consultations.choices import PatientStatus, Gender, RelationshipToChild, AppointmentStatus, AppointmentType

User = get_user_model()

class PatientsManagementBaseTestCase(APITestCase):
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

        # 3. Create Doctors for assignment testing
        self.test_doctor = User.objects.create_user(
            email='sarah.paul@nb.com', password='password123', first_name='Sarah', last_name='Paul'
        )
        UserRole.objects.create(user=self.test_doctor, role=self.doctor_role)

        # 4. Create Patients
        self.patient_1 = Patient.objects.create(
            patient_number='NBP-000001',
            parent_first_name='John',
            parent_last_name='Doe',
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number='9876543210',
            email='john.doe@example.com',
            child_first_name='Jimmy',
            child_last_name='Doe',
            date_of_birth=datetime.date(2020, 5, 15), # 6 years old in 2026
            gender=Gender.MALE,
            address='123 Park Lane',
            patient_status=PatientStatus.ACTIVE,
            assigned_doctor=self.test_doctor,
            created_by=self.receptionist_user
        )

        self.patient_2 = Patient.objects.create(
            patient_number='NBP-000002',
            parent_first_name='Jane',
            parent_last_name='Smith',
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number='9876543211',
            email='jane.smith@example.com',
            child_first_name='Sarah',
            child_last_name='Smith',
            date_of_birth=datetime.date(2018, 6, 20), # 8 years old in 2026
            gender=Gender.FEMALE,
            address='456 Oak Road',
            patient_status=PatientStatus.UNDER_TREATMENT,
            created_by=self.receptionist_user
        )


class PatientAPITests(PatientsManagementBaseTestCase):

    def test_statistics_api(self):
        """
        API 1: Patient Statistics
        """
        # Create an upcoming appointment for patient 1 to test metrics
        Appointment.objects.create(
            appointment_number='APT-00001',
            patient=self.patient_1,
            appointment_date=datetime.date.today() + datetime.timedelta(days=2),
            start_time=datetime.time(10, 0),
            end_time=datetime.time(11, 0),
            status=AppointmentStatus.CONFIRMED,
            booking_source='BACKOFFICE',
            appointment_type=AppointmentType.INITIAL,
            approved_by=self.receptionist_user,
            created_by=self.receptionist_user
        )

        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patients-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        data = response.data['data']
        self.assertEqual(data['total_patients'], 2)
        self.assertEqual(data['active_patients'], 1)
        self.assertEqual(data['under_treatment'], 1)
        self.assertEqual(data['male'], 1)
        self.assertEqual(data['female'], 1)
        self.assertEqual(data['upcoming_appointments'], 1)
        self.assertIn('average_age', data)

    def test_patients_list_api(self):
        """
        API 2: Patients List (with pagination and ordering)
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data['data'])
        self.assertEqual(len(response.data['data']['results']), 2)

        # Verify filters and search
        response = self.client.get(url, {'search': 'Jimmy'})
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['child_name'], 'Jimmy Doe')

        response = self.client.get(url, {'status': 'UNDER_TREATMENT'})
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['status'], 'UNDER_TREATMENT')

    def test_patient_details_api(self):
        """
        API 3: Patient Details
        """
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patients-detail', kwargs={'pk': self.patient_1.id})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['patient_id'], 'NBP-000001')
        self.assertEqual(data['child_first_name'], 'Jimmy')
        self.assertEqual(data['assigned_doctor']['id'], self.test_doctor.id)

    def test_create_patient_manual(self):
        """
        API 4: Create Patient
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-list')
        payload = {
            "child_first_name": "Daisy",
            "child_last_name": "Miller",
            "parent_first_name": "David",
            "parent_last_name": "Miller",
            "relationship_to_child": RelationshipToChild.FATHER,
            "mobile_number": "9998887776",
            "email": "daisy@example.com",
            "date_of_birth": "2020-10-10",
            "gender": Gender.FEMALE,
            "address": "Miller House",
            "patient_status": PatientStatus.ACTIVE
        }
        
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('patient_id', response.data['data'])
        
        # Check ActivityLog
        self.assertTrue(ActivityLog.objects.filter(action=ActivityType.PATIENT_CREATED).exists())

    def test_create_patient_validation(self):
        """
        API 4: Create Patient Validation (Future DOB & Duplicates)
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-list')

        # 1. Future DOB Rejection
        future_payload = {
            "child_first_name": "Daisy",
            "child_last_name": "Miller",
            "parent_first_name": "David",
            "parent_last_name": "Miller",
            "relationship_to_child": RelationshipToChild.FATHER,
            "mobile_number": "9998887776",
            "email": "daisy.future@example.com",
            "date_of_birth": "2050-10-10",
            "gender": Gender.FEMALE,
            "address": "Miller House",
            "patient_status": PatientStatus.ACTIVE
        }
        response = self.client.post(url, future_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_birth', response.data['errors'])

        # 2. Duplicate mobile + child name rejection
        duplicate_payload = {
            "child_first_name": "Jimmy",
            "child_last_name": "Doe",
            "parent_first_name": "John",
            "parent_last_name": "Doe",
            "relationship_to_child": RelationshipToChild.FATHER,
            "mobile_number": "9876543210", # Matches patient_1
            "email": "jimmy.dup@example.com",
            "date_of_birth": "2020-05-15",
            "gender": Gender.MALE,
            "address": "123 Park Lane",
            "patient_status": PatientStatus.ACTIVE
        }
        response = self.client.post(url, duplicate_payload)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_patient_read_only_fields(self):
        """
        API 5: Update Patient (blocking read-only modifications)
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-detail', kwargs={'pk': self.patient_1.id})
        
        payload = {
            "child_first_name": "James",
            "patient_number": "ATTEMPT-TO-CHANGE", # Read-only, should be skipped
            "patient_status": PatientStatus.FOLLOW_UP
        }
        response = self.client.patch(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify
        self.patient_1.refresh_from_db()
        self.assertEqual(self.patient_1.child_first_name, "James")
        self.assertEqual(self.patient_1.patient_number, "NBP-000001") # Untouched
        self.assertEqual(self.patient_1.patient_status, PatientStatus.FOLLOW_UP)

    def test_soft_delete_patient(self):
        """
        API 6: Soft Delete Patient
        """
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('patients-detail', kwargs={'pk': self.patient_1.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify database fields
        self.patient_1.refresh_from_db()
        self.assertTrue(self.patient_1.is_deleted)
        self.assertIsNotNone(self.patient_1.deleted_at)
        self.assertEqual(self.patient_1.deleted_by, self.admin_user)

        # Verify excluded from normal list queryset
        list_url = reverse('patients-list')
        list_response = self.client.get(list_url)
        self.assertEqual(len(list_response.data['data']['results']), 1) # Only patient 2 remains

    def test_filter_options_api(self):
        """
        API 7: Patient Filters Metadata
        """
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patients-filter-options')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertIn('statuses', data)
        self.assertIn('doctors', data)
        self.assertEqual(len(data['doctors']), 2) # Doctor User + Sarah Paul

    def test_quick_search_api(self):
        """
        API 8: Patient Quick Search Autocomplete
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-search')
        response = self.client.get(url, {'search': 'Jimmy'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 1)

    def test_export_patients_csv(self):
        """
        API 9: Export Patients CSV
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-export')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])

    def test_summary_chart_api(self):
        """
        API 10: Patient Summary Chart
        """
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patients-summary')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['Under Treatment'], 1)
        self.assertEqual(data['Active'], 1)

    def test_bulk_actions_api(self):
        """
        API 11: Bulk Actions
        """
        self.client.force_authenticate(user=self.receptionist_user)
        url = reverse('patients-bulk-actions')
        
        # Test bulk activate
        payload = {
            "patient_ids": [str(self.patient_1.id), str(self.patient_2.id)],
            "action": "activate"
        }
        response = self.client.post(url, payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.patient_1.refresh_from_db()
        self.patient_2.refresh_from_db()
        self.assertEqual(self.patient_1.patient_status, PatientStatus.ACTIVE)
        self.assertEqual(self.patient_2.patient_status, PatientStatus.ACTIVE)

    def test_recent_patients_api(self):
        """
        API 12: Recent Patients
        """
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patients-recent')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['data']), 2)

    def test_role_permissions_rbac(self):
        """
        Verifies role permissions restrictions.
        """
        # Doctor cannot create or update
        self.client.force_authenticate(user=self.doctor_user)
        url = reverse('patients-list')
        response = self.client.post(url, {})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Receptionist cannot delete
        self.client.force_authenticate(user=self.receptionist_user)
        delete_url = reverse('patients-detail', kwargs={'pk': self.patient_1.id})
        response = self.client.delete(delete_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
