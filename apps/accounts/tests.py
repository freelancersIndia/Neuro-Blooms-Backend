from django.utils import timezone
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import Role, UserRole, FailedLoginAttempt, AccountLock
from apps.accounts.models.otp import OTP
from apps.accounts.models.session import UserSession
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.roles import SystemRole
from apps.accounts.constants.otp_types import OTPPurpose
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.security_service import SecurityService

User = get_user_model()

class AccountsTestCase(APITestCase):
    def setUp(self):
        # Create default roles populated in migrations (just in case they don't populate in tests)
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)

        # Create basic test users
        self.admin_user = User.objects.create_user(
            email='admin@test.com',
            password='testpassword123',
            first_name='Admin',
            last_name='User'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        self.doctor_user = User.objects.create_user(
            email='doctor@test.com',
            password='testpassword123',
            first_name='Doctor',
            last_name='User'
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

    def test_user_role_helper_methods(self):
        # Test has_role
        self.assertTrue(self.admin_user.has_role(SystemRole.ADMIN))
        self.assertFalse(self.admin_user.has_role(SystemRole.DOCTOR))

        # Test has_any_role
        self.assertTrue(self.admin_user.has_any_role([SystemRole.ADMIN, SystemRole.DOCTOR]))
        self.assertFalse(self.admin_user.has_any_role([SystemRole.DOCTOR, SystemRole.RECEPTIONIST]))

        # Test multiple roles on a single user
        UserRole.objects.create(user=self.doctor_user, role=self.admin_role)
        self.assertTrue(self.doctor_user.has_role(SystemRole.ADMIN))
        self.assertTrue(self.doctor_user.has_role(SystemRole.DOCTOR))

    def test_login_successful_creates_session_and_activity_log(self):
        # 1. Send credentials to login view (expects OTP sent notification)
        url_login = reverse('auth_login')
        data = {
            'email': 'doctor@test.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url_login, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('sent', response.data['detail'].lower())

        # Retrieve the generated OTP from DB
        otp = OTP.objects.filter(user=self.doctor_user, purpose=OTPPurpose.LOGIN_VERIFICATION).first()
        self.assertIsNotNone(otp)

        # 2. Verify OTP code to log in and retrieve tokens
        url_verify = reverse('auth_verify_otp')
        response_verify = self.client.post(url_verify, {
            'email': 'doctor@test.com',
            'otp_code': otp.otp_code,
            'purpose': OTPPurpose.LOGIN_VERIFICATION
        })
        self.assertEqual(response_verify.status_code, status.HTTP_200_OK)
        self.assertIn('access', response_verify.data)
        self.assertIn('refresh', response_verify.data)
        self.assertIn('roles', response_verify.data['user'])
        self.assertEqual(response_verify.data['user']['roles'], [SystemRole.DOCTOR])

        # Check that session was created in DB
        sessions = UserSession.objects.filter(user=self.doctor_user, is_active=True)
        self.assertEqual(sessions.count(), 1)

        # Check that login activity log was created
        activity_logs = ActivityLog.objects.filter(user=self.doctor_user, action='LOGIN')
        self.assertEqual(activity_logs.count(), 1)

    def test_failed_login_creates_attempt_log_and_locks_after_5_failures(self):
        url = reverse('auth_login')
        data = {
            'email': 'doctor@test.com',
            'password': 'wrongpassword'
        }

        # 4 failed attempts should not lock
        for i in range(4):
            response = self.client.post(url, data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertFalse(SecurityService.is_account_locked(self.doctor_user))

        # 5th failed attempt triggers lock
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(SecurityService.is_account_locked(self.doctor_user))

        # Trying to login with correct credentials while locked should fail
        correct_data = {
            'email': 'doctor@test.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, correct_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('locked', response.data['detail'].lower())

    def test_otp_generation_email_sending_and_verification(self):
        # Generate LOGIN_VERIFICATION OTP
        otp = OTPService.generate_otp(self.doctor_user, OTPPurpose.LOGIN_VERIFICATION)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertEqual(otp.purpose, OTPPurpose.LOGIN_VERIFICATION)
        self.assertFalse(otp.is_used)

        # Verify correct OTP
        url = reverse('auth_verify_otp')
        data = {
            'email': 'doctor@test.com',
            'otp_code': otp.otp_code,
            'purpose': OTPPurpose.LOGIN_VERIFICATION
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data) # Login OTP verify returns JWT tokens!

        # Try to reuse the OTP
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_flow(self):
        # 1. Request forgot password OTP
        url_forgot = reverse('auth_forgot_password')
        response = self.client.post(url_forgot, {'email': 'doctor@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Fetch generated OTP from DB
        otp = OTP.objects.filter(user=self.doctor_user, purpose=OTPPurpose.PASSWORD_RESET).first()
        self.assertIsNotNone(otp)

        # 2. Verify OTP to get signed verification token
        url_verify = reverse('auth_verify_otp')
        response_verify = self.client.post(url_verify, {
            'email': 'doctor@test.com',
            'otp_code': otp.otp_code,
            'purpose': OTPPurpose.PASSWORD_RESET
        })
        self.assertEqual(response_verify.status_code, status.HTTP_200_OK)
        token = response_verify.data['token']
        self.assertIsNotNone(token)

        # 3. Reset password using token
        url_reset = reverse('auth_reset_password')
        response_reset = self.client.post(url_reset, {
            'token': token,
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response_reset.status_code, status.HTTP_200_OK)

        # Verify password is changed
        self.doctor_user.refresh_from_db()
        self.assertTrue(self.doctor_user.check_password('newpassword123'))

    def test_session_list_and_revocation(self):
        # 1. Login with credentials
        url_login = reverse('auth_login')
        data = {
            'email': 'doctor@test.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url_login, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Get generated OTP
        otp = OTP.objects.filter(user=self.doctor_user, purpose=OTPPurpose.LOGIN_VERIFICATION).first()

        # 2. Verify OTP code to log in
        url_verify = reverse('auth_verify_otp')
        response_verify = self.client.post(url_verify, {
            'email': 'doctor@test.com',
            'otp_code': otp.otp_code,
            'purpose': OTPPurpose.LOGIN_VERIFICATION
        })
        self.assertEqual(response_verify.status_code, status.HTTP_200_OK)
        access_token = response_verify.data['access']
        refresh_token = response_verify.data['refresh']

        # Get session list
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url_sessions = reverse('sessions-list')
        response = self.client.get(url_sessions)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        session_id = response.data[0]['id']

        # Revoke session
        url_session_detail = reverse('sessions-detail', args=[session_id])
        response = self.client.delete(url_session_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Attempting refresh token request with revoked session should fail
        url_refresh = reverse('token_refresh')
        response = self.client.post(url_refresh, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_email_sending_failure_does_not_crash_flow(self):
        from unittest.mock import patch

        # Mock send_mail to raise ConnectionRefusedError
        with patch('apps.accounts.services.email_service.send_mail') as mock_send_mail:
            mock_send_mail.side_effect = ConnectionRefusedError("Connection refused mock error")

            # Request forgot password OTP (which triggers send_password_reset_otp)
            url_forgot = reverse('auth_forgot_password')
            response = self.client.post(url_forgot, {'email': 'doctor@test.com'})

            # The flow should succeed (return 200 OK) because the email service catches the error
            self.assertEqual(response.status_code, status.HTTP_200_OK)

            # Verify OTP is still generated in the database even if email sending failed
            otp = OTP.objects.filter(user=self.doctor_user, purpose=OTPPurpose.PASSWORD_RESET).first()
            self.assertIsNotNone(otp)

            # Verify the mock was indeed called
            mock_send_mail.assert_called_once()

    def test_passing_digit_otp_instead_of_signed_token_raises_clear_error(self):
        url_reset = reverse('auth_reset_password')
        response = self.client.post(url_reset, {
            'token': '123456',
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('passed the 6-digit OTP code', response.data['detail'])


