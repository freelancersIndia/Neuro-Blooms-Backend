from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from rest_framework import status
from apps.accounts.models.otp import OTP
from apps.accounts.models.session import UserSession
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.roles import SystemRole
from apps.accounts.constants.otp_types import OTPPurpose
from apps.accounts.services.otp_service import OTPService
from apps.accounts.services.security_service import SecurityService

from .base import AccountsBaseTestCase

class AccountsAuthTests(AccountsBaseTestCase):
    def test_user_role_helper_methods(self):
        # Test has_role
        self.assertTrue(self.admin_user.has_role(SystemRole.ADMIN))
        self.assertFalse(self.admin_user.has_role(SystemRole.DOCTOR))

        # Test has_any_role
        self.assertTrue(self.admin_user.has_any_role([SystemRole.ADMIN, SystemRole.DOCTOR]))
        self.assertFalse(self.admin_user.has_any_role([SystemRole.DOCTOR, SystemRole.RECEPTIONIST]))

        # Test multiple roles on a single user
        from apps.accounts.models.user import UserRole
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
        self.assertTrue(response.data['success'])
        self.assertIn('sent', response.data['message'].lower())

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
        self.assertTrue(response_verify.data['success'])
        self.assertIn('access', response_verify.data['data'])
        self.assertIn('refresh', response_verify.data['data'])
        self.assertIn('roles', response_verify.data['data']['user'])
        self.assertEqual(response_verify.data['data']['user']['roles'], [SystemRole.DOCTOR])
        self.assertIn('profile_image', response_verify.data['data']['user'])
        self.assertIsNone(response_verify.data['data']['user']['profile_image'])

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
            self.assertFalse(response.data['success'])
            self.assertFalse(SecurityService.is_account_locked(self.doctor_user))

        # 5th failed attempt triggers lock
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertTrue(SecurityService.is_account_locked(self.doctor_user))

        # Trying to login with correct credentials while locked should fail
        correct_data = {
            'email': 'doctor@test.com',
            'password': 'testpassword123'
        }
        response = self.client.post(url, correct_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('locked', response.data['message'].lower())

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
        self.assertTrue(response.data['success'])
        self.assertIn('access', response.data['data'])

        # Try to reuse the OTP
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_password_reset_flow(self):
        # 1. Request forgot password OTP
        url_forgot = reverse('auth_forgot_password')
        response = self.client.post(url_forgot, {'email': 'doctor@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

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
        self.assertTrue(response_verify.data['success'])
        token = response_verify.data['data']['token']
        self.assertIsNotNone(token)

        # 3. Reset password using token
        url_reset = reverse('auth_reset_password')
        response_reset = self.client.post(url_reset, {
            'token': token,
            'new_password': 'newpassword123',
            'confirm_password': 'newpassword123'
        })
        self.assertEqual(response_reset.status_code, status.HTTP_200_OK)
        self.assertTrue(response_reset.data['success'])

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
        access_token = response_verify.data['data']['access']
        refresh_token = response_verify.data['data']['refresh']

        # Get session list
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        url_sessions = reverse('sessions-list')
        response = self.client.get(url_sessions)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(len(response.data['data']), 1)
        session_id = response.data['data'][0]['id']

        # Revoke session
        url_session_detail = reverse('sessions-detail', args=[session_id])
        response = self.client.delete(url_session_detail)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Attempting refresh token request with revoked session should fail
        url_refresh = reverse('token_refresh')
        response = self.client.post(url_refresh, {'refresh': refresh_token})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Session expired or revoked.")

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
            self.assertTrue(response.data['success'])

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
        self.assertFalse(response.data['success'])
        self.assertIn('passed the 6-digit OTP code', response.data['message'])

    def test_resend_verification_otp(self):
        # 1. Post to resend verification endpoint
        url_resend = reverse('auth_resend_verification')
        response = self.client.post(url_resend, {'email': 'doctor@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Verify email verification OTP is generated in DB
        otp = OTP.objects.filter(user=self.doctor_user, purpose=OTPPurpose.EMAIL_VERIFICATION).first()
        self.assertIsNotNone(otp)

        # Verify activity log was recorded
        log = ActivityLog.objects.filter(user=self.doctor_user, action='EMAIL_VERIFICATION_SENT').first()
        self.assertIsNotNone(log)

    def test_email_verification_completion(self):
        # Generate an email verification OTP
        otp = OTPService.generate_otp(self.doctor_user, OTPPurpose.EMAIL_VERIFICATION)
        
        # Verify the OTP using verify-otp endpoint
        url_verify = reverse('auth_verify_otp')
        response = self.client.post(url_verify, {
            'email': 'doctor@test.com',
            'otp_code': otp.otp_code,
            'purpose': OTPPurpose.EMAIL_VERIFICATION
        })
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIsNone(response.data['data'])
        self.assertEqual(response.data['message'], "Email verified successfully.")

        # Check user status in DB
        self.doctor_user.refresh_from_db()
        self.assertTrue(self.doctor_user.is_verified)

        # Check EMAIL_VERIFIED activity log
        log = ActivityLog.objects.filter(user=self.doctor_user, action='EMAIL_VERIFIED').first()
        self.assertIsNotNone(log)

    def test_account_unlock_api(self):
        from apps.accounts.models.user import AccountLock, FailedLoginAttempt
        # 1. Lock the user account
        unlock_time = timezone.now() + timedelta(minutes=15)
        lock = AccountLock.objects.create(
            user=self.doctor_user,
            unlock_at=unlock_time,
            reason="TOO_MANY_FAILED_ATTEMPTS",
            is_active=True
        )
        FailedLoginAttempt.objects.create(email=self.doctor_user.email, ip_address='127.0.0.1', reason='TEST')

        # 2. Login as admin and attempt to unlock
        login_url = reverse('auth_login')
        response = self.client.post(login_url, {'email': 'admin@test.com', 'password': 'testpassword123'})
        admin_otp = OTP.objects.filter(user=self.admin_user, purpose=OTPPurpose.LOGIN_VERIFICATION).first()
        
        verify_url = reverse('auth_verify_otp')
        response_verify = self.client.post(verify_url, {
            'email': 'admin@test.com',
            'otp_code': admin_otp.otp_code,
            'purpose': OTPPurpose.LOGIN_VERIFICATION
        })
        access_token = response_verify.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        # 3. Call the unlock API
        unlock_url = reverse('users-unlock', args=[self.doctor_user.id])
        response_unlock = self.client.post(unlock_url)
        self.assertEqual(response_unlock.status_code, status.HTTP_200_OK)
        self.assertTrue(response_unlock.data['success'])
        self.assertEqual(response_unlock.data['message'], "User account unlocked successfully.")

        # Verify database state
        lock.refresh_from_db()
        self.assertFalse(lock.is_active)
        self.assertEqual(FailedLoginAttempt.objects.filter(email=self.doctor_user.email).count(), 0)

        # Verify activity log
        log = ActivityLog.objects.filter(user=self.doctor_user, action='ACCOUNT_UNLOCKED').first()
        self.assertIsNotNone(log)

    def test_profile_me_endpoint(self):
        # Login
        login_url = reverse('auth_login')
        response = self.client.post(login_url, {'email': 'doctor@test.com', 'password': 'testpassword123'})
        doctor_otp = OTP.objects.filter(user=self.doctor_user, purpose=OTPPurpose.LOGIN_VERIFICATION).first()
        
        verify_url = reverse('auth_verify_otp')
        response_verify = self.client.post(verify_url, {
            'email': 'doctor@test.com',
            'otp_code': doctor_otp.otp_code,
            'purpose': OTPPurpose.LOGIN_VERIFICATION
        })
        access_token = response_verify.data['data']['access']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')

        url = reverse('profile_me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['email'], 'doctor@test.com')
        self.assertEqual(response.data['data']['first_name'], 'Doctor')
        self.assertEqual(response.data['data']['last_name'], 'User')
        self.assertIsNone(response.data['data']['specialization'])
        self.assertEqual(response.data['data']['qualification'], None)
        self.assertEqual(response.data['data']['experience'], 0)
        self.assertTrue(response.data['data']['is_active'])
        self.assertIsNotNone(response.data['data']['last_login'])

        # Update profile details
        patch_data = {
            'first_name': 'UpdatedDoctor',
            'specialization': 'Neuroscience',
            'qualification': 'PhD',
            'experience': 5
        }
        response = self.client.patch(url, patch_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['first_name'], 'UpdatedDoctor')
        self.assertEqual(response.data['data']['specialization'], 'Neuroscience')
        self.assertEqual(response.data['data']['qualification'], 'PhD')
        self.assertEqual(response.data['data']['experience'], 5)

        # Verify DB changes
        self.doctor_user.refresh_from_db()
        self.assertEqual(self.doctor_user.first_name, 'UpdatedDoctor')
        self.assertEqual(self.doctor_user.specialization, 'Neuroscience')
        self.assertEqual(self.doctor_user.qualification, 'PhD')
        self.assertEqual(self.doctor_user.experience, 5)
