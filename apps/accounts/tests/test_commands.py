from django.core.management import call_command
from django.contrib.auth import get_user_model
from apps.accounts.models.user import Role
from .base import AccountsBaseTestCase

User = get_user_model()

class AccountsCommandsTests(AccountsBaseTestCase):
    def test_seed_roles_command(self):
        # Call management command
        call_command('seed_roles')
        
        # Verify roles exist
        self.assertTrue(Role.objects.filter(name='ADMIN').exists())
        self.assertTrue(Role.objects.filter(name='DOCTOR').exists())
        self.assertTrue(Role.objects.filter(name='RECEPTIONIST').exists())

    def test_create_initial_admin_command(self):
        import os
        from unittest.mock import patch

        # Mock environment variables
        env = {
            'INITIAL_ADMIN_EMAIL': 'newadmin@test.com',
            'INITIAL_ADMIN_PASSWORD': 'SecurePassword123',
            'INITIAL_ADMIN_FIRST_NAME': 'Initial',
            'INITIAL_ADMIN_LAST_NAME': 'Admin'
        }
        with patch.dict(os.environ, env):
            call_command('create_initial_admin')

        # Verify user was created
        user = User.objects.filter(email='newadmin@test.com').first()
        self.assertIsNotNone(user)
        self.assertTrue(user.is_verified)
        self.assertTrue(user.is_active)
        self.assertTrue(user.has_role('ADMIN'))
