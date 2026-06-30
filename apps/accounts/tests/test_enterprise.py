from django.urls import reverse
from django.utils import timezone
from django.db.models import Q
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import User, Role, UserRole
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.roles import SystemRole
from apps.accounts.constants.otp_types import OTPPurpose
from apps.accounts.constants.activity_types import ActivityType

class EnterpriseUserManagementTests(APITestCase):
    def setUp(self):
        super().setUp()
        # Create default roles
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
            last_name='User',
            phone_number='1234567890'
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        self.client.force_authenticate(user=self.admin_user)
        
        # Create a few more users for statistics and filtering
        self.inactive_user = User.objects.create_user(
            email='inactive@test.com',
            password='testpassword123',
            first_name='Inactive',
            last_name='User',
            is_active=False
        )
        
        self.verified_user = User.objects.create_user(
            email='verified@test.com',
            password='testpassword123',
            first_name='Verified',
            last_name='User',
            is_verified=True
        )
        
        self.blocked_user = User.objects.create_user(
            email='blocked@test.com',
            password='testpassword123',
            first_name='Blocked',
            last_name='User',
            is_blocked=True
        )

    def test_get_statistics(self):
        url = reverse('users-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['total_users'], User.objects.filter(is_deleted=False).count())
        self.assertEqual(data['active_users'], User.objects.filter(is_active=True, is_deleted=False).count())
        self.assertEqual(data['inactive_users'], User.objects.filter(is_active=False, is_deleted=False).count())
        self.assertEqual(data['locked_users'], User.objects.filter(Q(is_blocked=True) | Q(locks__is_active=True, locks__unlock_at__gt=timezone.now())).distinct().count())

    def test_list_users_filters(self):
        url = reverse('users-list')
        
        # Filter by active
        response = self.client.get(url, {'active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        for u in response.data['data']['results']:
            self.assertTrue(u['is_active'])
            
        # Filter by blocked
        response = self.client.get(url, {'blocked': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(u['email'] == 'blocked@test.com' for u in response.data['data']['results']))

    def test_block_and_unlock_user(self):
        # Block user
        url_block = reverse('users-block', args=[self.doctor_user.id])
        response = self.client.post(url_block)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertTrue(self.doctor_user.is_blocked)
        
        # Unlock user
        url_unlock = reverse('users-unlock', args=[self.doctor_user.id])
        response = self.client.post(url_unlock)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertFalse(self.doctor_user.is_blocked)

    def test_activate_and_deactivate_user(self):
        # Deactivate user
        url_deactivate = reverse('users-deactivate', args=[self.doctor_user.id])
        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertFalse(self.doctor_user.is_active)
        
        # Activate user
        url_activate = reverse('users-activate', args=[self.doctor_user.id])
        response = self.client.post(url_activate)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertTrue(self.doctor_user.is_active)

    def test_self_block_deactivate_delete_fails(self):
        # Block self
        url_block = reverse('users-block', args=[self.admin_user.id])
        response = self.client.post(url_block)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Deactivate self
        url_deactivate = reverse('users-deactivate', args=[self.admin_user.id])
        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Delete self
        url_delete = reverse('users-detail', args=[self.admin_user.id])
        response = self.client.delete(url_delete)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_final_admin_protection_rules(self):
        # Try to deactivate the only admin
        url_deactivate = reverse('users-deactivate', args=[self.admin_user.id])
        response = self.client.post(url_deactivate)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Try to remove ADMIN role from the only admin
        url_remove_role = reverse('users-roles-remove', args=[self.admin_user.id])
        response = self.client.post(url_remove_role, {'roles': ['ADMIN']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_and_remove_user_roles(self):
        # Assign DOCTOR role to verified_user
        url_assign = reverse('users-roles-assign', args=[self.verified_user.id])
        response = self.client.post(url_assign, {'roles': ['DOCTOR']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.verified_user.has_role('DOCTOR'))
        
        # Remove DOCTOR role
        url_remove = reverse('users-roles-remove', args=[self.verified_user.id])
        response = self.client.post(url_remove, {'roles': ['DOCTOR']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.verified_user.has_role('DOCTOR'))

    def test_reset_password(self):
        url = reverse('users-reset-password', args=[self.doctor_user.id])
        response = self.client.post(url, {'password': 'NewPassword123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.doctor_user.refresh_from_db()
        self.assertTrue(self.doctor_user.check_password('NewPassword123'))

    def test_session_list_and_revocation(self):
        from apps.accounts.models.session import UserSession
        # Create multiple sessions
        UserSession.objects.create(user=self.doctor_user, refresh_token_jti='jti-1', is_active=True)
        UserSession.objects.create(user=self.doctor_user, refresh_token_jti='jti-2', is_active=True)
        
        url_list = reverse('users-sessions', args=[self.doctor_user.id])
        response = self.client.get(url_list)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 2)
        
        # Revoke session
        session = UserSession.objects.filter(user=self.doctor_user, is_active=True).first()
        url_revoke = reverse('user_session_revoke', args=[self.doctor_user.id, session.id])
        response = self.client.post(url_revoke)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        session.refresh_from_db()
        self.assertFalse(session.is_active)

    def test_logout_all_sessions(self):
        from apps.accounts.models.session import UserSession
        # Create multiple sessions
        UserSession.objects.create(user=self.doctor_user, refresh_token_jti='jti-1', is_active=True)
        UserSession.objects.create(user=self.doctor_user, refresh_token_jti='jti-2', is_active=True)
        
        url = reverse('users-logout-all', args=[self.doctor_user.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(self.doctor_user.sessions.filter(is_active=True).count(), 0)

    def test_get_user_activity_and_security_logs(self):
        # Create activity log
        ActivityLog.objects.create(
            user=self.admin_user,
            target_user=self.doctor_user,
            action=ActivityType.USER_UPDATED,
            description="Admin updated doctor user",
            ip_address="127.0.0.1"
        )
        
        # Create security log
        ActivityLog.objects.create(
            user=self.doctor_user,
            target_user=self.doctor_user,
            action=ActivityType.LOGIN,
            description="User logged in",
            ip_address="127.0.0.1"
        )
        
        url_activity = reverse('users-activity', args=[self.doctor_user.id])
        response = self.client.get(url_activity)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 2)
        
        url_security = reverse('users-security', args=[self.doctor_user.id])
        response = self.client.get(url_security)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)

    def test_security_logs_filtering_and_pagination(self):
        # Create activity logs
        ActivityLog.objects.create(user=self.doctor_user, action=ActivityType.LOGIN, description='Doc Login')
        ActivityLog.objects.create(user=self.admin_user, action=ActivityType.USER_CREATED, description='Admin created user')

        # Test filter by action
        url = reverse('security_logs')
        response = self.client.get(url, {'action': 'USER_CREATED'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['description'], 'Admin created user')

        # Test filter by user_id
        response = self.client.get(url, {'user_id': self.doctor_user.id})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['description'], 'Doc Login')
