import datetime
from unittest.mock import patch
from django.utils import timezone
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.consultations.models import AppointmentRequest
from apps.consultations.choices import (
    Gender,
    RelationshipToChild,
    AppointmentType,
    PrimaryConcern,
    AppointmentRequestStatus,
    BookingSource,
)
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class PublicConsultationRequestAPITests(APITestCase):
    def setUp(self):
        self.url = reverse('public_consultation_request')
        self.valid_payload = {
            "parent_first_name": "Rohan",
            "parent_last_name": "Sharma",
            "relationship_to_child": "Father",
            "mobile_number": "9876543210",
            "alternate_mobile_number": "9876543211",
            "email": "rohan.sharma@example.com",
            "child_first_name": "Aarav",
            "child_last_name": "Sharma",
            "date_of_birth": "2020-05-15",
            "gender": "Male",
            "appointment_type": "INITIAL_CONSULTATION",
            "primary_concern": "Speech Delay",
            "preferred_date": str(timezone.now().date() + datetime.timedelta(days=10)),
            "preferred_time_slot": "10:00 AM",
            "additional_notes": "Needs patience.",
            "referral_source": "Google Search"
        }

    @patch('apps.accounts.services.email_service.send_mail')
    def test_submit_consultation_request_success(self, mock_send_mail):
        """
        Verify that a valid consultation request can be submitted.
        """
        response = self.client.post(self.url, self.valid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "Consultation request submitted successfully.")
        
        data = response.data['data']
        self.assertTrue(data['request_number'].startswith(f"REQ-{datetime.date.today().year}-"))
        self.assertEqual(data['status'], "PENDING")
        self.assertEqual(data['preferred_date'], self.valid_payload['preferred_date'])
        self.assertEqual(data['preferred_time_slot'], "10:00 AM")

        # Database assertions
        db_request = AppointmentRequest.objects.get(request_number=data['request_number'])
        self.assertEqual(db_request.parent_first_name, "Rohan")
        self.assertEqual(db_request.parent_last_name, "Sharma")
        # Choice normalization verification
        self.assertEqual(db_request.relationship_to_child, RelationshipToChild.FATHER)
        self.assertEqual(db_request.gender, Gender.MALE)
        self.assertEqual(db_request.appointment_type, AppointmentType.INITIAL_CONSULTATION)
        self.assertEqual(db_request.primary_concern, PrimaryConcern.SPEECH_DELAY)
        self.assertEqual(db_request.booking_source, BookingSource.WEBSITE)
        self.assertEqual(db_request.status, AppointmentRequestStatus.PENDING)

        # Activity log assertion
        activity = ActivityLog.objects.filter(
            action=ActivityType.CONSULTATION_REQUEST_CREATED,
            user=None
        ).first()
        self.assertIsNotNone(activity)
        self.assertIn(db_request.request_number, activity.description)

        # Email assertion
        mock_send_mail.assert_called_once()

    @patch('apps.accounts.services.email_service.send_mail')
    def test_choice_normalization_variations(self, mock_send_mail):
        """
        Verify case-insensitivity and display label vs key handling.
        """
        payload = self.valid_payload.copy()
        payload.update({
            "relationship_to_child": "mother",  # lower case of label
            "gender": "PREFER_NOT_TO_SAY",      # exact key
            "appointment_type": "development_assessment", # lower case of key
            "primary_concern": "AUTISM_ASSESSMENT" # key representation
        })

        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        db_request = AppointmentRequest.objects.get(request_number=response.data['data']['request_number'])
        self.assertEqual(db_request.relationship_to_child, RelationshipToChild.MOTHER)
        self.assertEqual(db_request.gender, Gender.PREFER_NOT_TO_SAY)
        self.assertEqual(db_request.appointment_type, AppointmentType.DEVELOPMENT_ASSESSMENT)
        self.assertEqual(db_request.primary_concern, PrimaryConcern.AUTISM_ASSESSMENT)

    def test_validation_missing_required_fields(self):
        """
        Verify validation fails for missing required fields.
        """
        invalid_payload = {
            "parent_last_name": "Sharma"
            # Missing other required fields
        }
        response = self.client.post(self.url, invalid_payload, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Validation failed.")
        self.assertIn('parent_first_name', response.data['errors'])

    def test_validation_invalid_indian_mobile(self):
        """
        Verify mobile number format validation.
        """
        payload = self.valid_payload.copy()
        invalid_mobiles = ["1234567890", "98765", "98765432109", "abcde12345"]
        
        for mobile in invalid_mobiles:
            payload['mobile_number'] = mobile
            response = self.client.post(self.url, payload, format='json')
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.data['errors']['mobile_number'], ["Enter a valid mobile number."])

    def test_validation_future_date_of_birth(self):
        """
        Verify date of birth cannot be in the future.
        """
        payload = self.valid_payload.copy()
        future_date = str(timezone.now().date() + datetime.timedelta(days=1))
        payload['date_of_birth'] = future_date
        
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('date_of_birth', response.data['errors'])

    def test_validation_past_preferred_date(self):
        """
        Verify preferred date cannot be in the past.
        """
        payload = self.valid_payload.copy()
        past_date = str(timezone.now().date() - datetime.timedelta(days=1))
        payload['preferred_date'] = past_date
        
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('preferred_date', response.data['errors'])

    def test_validation_other_primary_concern_requires_additional_notes(self):
        """
        Verify additional_notes is required if primary_concern is 'Other'.
        """
        payload = self.valid_payload.copy()
        payload['primary_concern'] = "Other"
        payload['additional_notes'] = ""  # Empty notes
        
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('additional_notes', response.data['errors'])
        
        # Non-empty notes should succeed
        payload['additional_notes'] = "My concern detail."
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @patch('apps.accounts.services.email_service.send_mail')
    def test_duplicate_request_prevention(self, mock_send_mail):
        """
        Verify duplicate request prevention returns a 409 Conflict.
        """
        # Create first request
        response_1 = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response_1.status_code, status.HTTP_201_CREATED)
        
        # Attempt identical request
        response_2 = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response_2.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(response_2.data['success'])
        self.assertEqual(
            response_2.data['message'],
            "A consultation request already exists for this child on the selected date."
        )

        # Attempt same details but different preferred date - should succeed
        different_date_payload = self.valid_payload.copy()
        different_date_payload['preferred_date'] = str(timezone.now().date() + datetime.timedelta(days=12))
        response_3 = self.client.post(self.url, different_date_payload, format='json')
        self.assertEqual(response_3.status_code, status.HTTP_201_CREATED)

    @patch('apps.accounts.services.email_service.send_mail')
    def test_resilience_to_email_failures(self, mock_send_mail):
        """
        Verify that email failure does not prevent request creation.
        """
        mock_send_mail.side_effect = Exception("SMTP Server Down")
        
        response = self.client.post(self.url, self.valid_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        
        # Verify db request actually created
        self.assertEqual(
            AppointmentRequest.objects.filter(request_number=response.data['data']['request_number']).count(), 
            1
        )


class AppointmentRequestManagementAPITests(APITestCase):
    def setUp(self):
        from django.contrib.auth import get_user_model
        from apps.accounts.models.user import Role, UserRole
        from apps.accounts.constants.roles import SystemRole

        User = get_user_model()

        # Create system roles
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)

        # Create test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpassword123',
            first_name='Admin',
            last_name='User'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.receptionist_user = User.objects.create_user(
            email='receptionist@test.com',
            password='testpassword123',
            first_name='Receptionist',
            last_name='User'
        )
        UserRole.objects.create(user=self.receptionist_user, role=self.receptionist_role)

        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            password='testpassword123',
            first_name='Doctor',
            last_name='User'
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Create sample appointment requests
        self.request_1 = AppointmentRequest.objects.create(
            request_number="REQ-2026-000001",
            parent_first_name="Rohan",
            parent_last_name="Sharma",
            relationship_to_child=RelationshipToChild.FATHER,
            mobile_number="9876543210",
            email="rohan@example.com",
            child_first_name="Aarav",
            child_last_name="Sharma",
            date_of_birth=datetime.date(2020, 5, 15),
            gender=Gender.MALE,
            appointment_type=AppointmentType.INITIAL_CONSULTATION,
            primary_concern=PrimaryConcern.SPEECH_DELAY,
            preferred_date=timezone.now().date() + datetime.timedelta(days=5),
            preferred_time_slot="10:00 AM",
            booking_source=BookingSource.WEBSITE,
            status=AppointmentRequestStatus.PENDING
        )

        self.request_2 = AppointmentRequest.objects.create(
            request_number="REQ-2026-000002",
            parent_first_name="Anjali",
            parent_last_name="Verma",
            relationship_to_child=RelationshipToChild.MOTHER,
            mobile_number="8765432109",
            email="anjali@example.com",
            child_first_name="Kiara",
            child_last_name="Verma",
            date_of_birth=datetime.date(2021, 8, 20),
            gender=Gender.FEMALE,
            appointment_type=AppointmentType.DEVELOPMENT_ASSESSMENT,
            primary_concern=PrimaryConcern.AUTISM_ASSESSMENT,
            preferred_date=timezone.now().date() + datetime.timedelta(days=6),
            preferred_time_slot="11:30 AM",
            booking_source=BookingSource.WEBSITE,
            status=AppointmentRequestStatus.APPROVED
        )

        # Activity log for request_1 submission
        ActivityLog.objects.create(
            user=None,
            action=ActivityType.CONSULTATION_REQUEST_CREATED,
            description=f"Public consultation request submitted. Request Number: {self.request_1.request_number}"
        )

        # URLs
        self.list_url = reverse('appointment_request_list')
        self.stats_url = reverse('appointment_request_statistics')
        self.export_url = reverse('appointment_request_export')
        
    def test_list_requests_authorization(self):
        """
        Verify list requests endpoint permissions (Admin/Receptionist allowed, Doctor forbidden).
        """
        # Unauthenticated
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Doctor user (forbidden)
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Receptionist user (allowed)
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('statistics', response.data['data'])
        self.assertEqual(len(response.data['data']['results']), 2)

        # Admin user (allowed)
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_requests_searching_and_filtering(self):
        """
        Verify listing search queries and filters work.
        """
        self.client.force_authenticate(user=self.admin_user)

        # Search by child name
        response = self.client.get(self.list_url, {'search': 'Aarav'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['pagination']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['request_number'], "REQ-2026-000001")

        # Filter by status
        response = self.client.get(self.list_url, {'status': 'APPROVED'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['pagination']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['request_number'], "REQ-2026-000002")

    def test_list_requests_ordering(self):
        """
        Verify listing ordering applies.
        """
        self.client.force_authenticate(user=self.admin_user)
        
        # Order by parent_first_name ascending (Anjali comes first)
        response = self.client.get(self.list_url, {'ordering': 'parent_first_name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['results'][0]['parent_first_name'], "Anjali")

        # Order by parent_first_name descending (Rohan comes first)
        response = self.client.get(self.list_url, {'ordering': '-parent_first_name'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['results'][0]['parent_first_name'], "Rohan")

    def test_detail_request(self):
        """
        Verify request detail is retrieved and viewed action is logged.
        """
        url = reverse('appointment_request_detail', kwargs={'id': self.request_1.id})
        
        # Doctor forbidden
        self.client.force_authenticate(user=self.doctor_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Receptionist allowed
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['request_number'], self.request_1.request_number)
        
        # Check that VIEWED activity log is recorded
        viewed_log = ActivityLog.objects.filter(
            action='APPOINTMENT_REQUEST_VIEWED',
            user=self.receptionist_user
        ).first()
        self.assertIsNotNone(viewed_log)
        self.assertIn(self.request_1.request_number, viewed_log.description)

    def test_statistics_endpoint(self):
        """
        Verify request aggregate stats.
        """
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.get(self.stats_url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['total_requests'], 2)
        self.assertEqual(data['pending_review'], 1)
        self.assertEqual(data['approved'], 1)
        self.assertEqual(data['rejected'], 0)

    @patch('apps.accounts.services.email_service.send_mail')
    def test_approve_request(self, mock_send_mail):
        """
        Verify request approval and activity logs creation.
        """
        url = reverse('appointment_request_approve', kwargs={'id': self.request_1.id})
        self.client.force_authenticate(user=self.receptionist_user)

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "Appointment request approved successfully.")

        # Database assertions
        db_request = AppointmentRequest.objects.get(id=self.request_1.id)
        self.assertEqual(db_request.status, AppointmentRequestStatus.APPROVED)
        self.assertEqual(db_request.reviewed_by, self.receptionist_user)
        self.assertIsNotNone(db_request.reviewed_at)

        # Activity log verification
        appr_log = ActivityLog.objects.filter(
            action='APPOINTMENT_REQUEST_APPROVED',
            user=self.receptionist_user
        ).first()
        self.assertIsNotNone(appr_log)
        self.assertIn(db_request.request_number, appr_log.description)

        # Email verification
        mock_send_mail.assert_called_once()

    def test_approve_request_conflicts(self):
        """
        Verify conflict response when approving already approved requests.
        """
        url = reverse('appointment_request_approve', kwargs={'id': self.request_2.id})  # Already approved
        self.client.force_authenticate(user=self.receptionist_user)

        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)
        self.assertFalse(response.data['success'])

    def test_reject_request(self):
        """
        Verify request rejection.
        """
        url = reverse('appointment_request_reject', kwargs={'id': self.request_1.id})
        self.client.force_authenticate(user=self.receptionist_user)

        # Rejection payload without reason
        response = self.client.post(url, {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('reason', response.data['errors'])

        # Rejection payload with valid reason
        payload = {"reason": "Duplicate request details."}
        response = self.client.post(url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Database assertions
        db_request = AppointmentRequest.objects.get(id=self.request_1.id)
        self.assertEqual(db_request.status, AppointmentRequestStatus.REJECTED)
        self.assertEqual(db_request.rejection_reason, "Duplicate request details.")

        # Activity log verification
        rej_log = ActivityLog.objects.filter(
            action='APPOINTMENT_REQUEST_REJECTED',
            user=self.receptionist_user
        ).first()
        self.assertIsNotNone(rej_log)
        self.assertIn(db_request.request_number, rej_log.description)

    def test_timeline_endpoint(self):
        """
        Verify timeline logs list retrieval.
        """
        timeline_url = reverse('appointment_request_timeline', kwargs={'id': self.request_1.id})
        self.client.force_authenticate(user=self.receptionist_user)

        # View details to generate VIEWED log
        detail_url = reverse('appointment_request_detail', kwargs={'id': self.request_1.id})
        self.client.get(detail_url)

        # Get timeline
        response = self.client.get(timeline_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        timeline_data = response.data['data']
        self.assertEqual(len(timeline_data), 2)
        self.assertEqual(timeline_data[0]['event'], "Submitted")
        self.assertEqual(timeline_data[0]['performed_by'], "Website")
        self.assertEqual(timeline_data[1]['event'], "Viewed")
        self.assertEqual(timeline_data[1]['performed_by'], self.receptionist_user.email)

    def test_export_csv_endpoint(self):
        """
        Verify requests export streaming CSV response.
        """
        self.client.force_authenticate(user=self.receptionist_user)
        response = self.client.get(self.export_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'text/csv')
        self.assertIn('attachment', response['Content-Disposition'])
        
        # Read streaming response content
        content = b"".join(response.streaming_content).decode('utf-8')
        lines = content.split('\r\n')
        
        # Verify headers
        self.assertIn('Request Number', lines[0])
        # Verify request 1 and 2 details exist
        self.assertTrue(any(self.request_1.request_number in line for line in lines))
        self.assertTrue(any(self.request_2.request_number in line for line in lines))

