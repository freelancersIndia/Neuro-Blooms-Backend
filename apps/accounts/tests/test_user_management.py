from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import User, Role, UserRole, FailedLoginAttempt, AccountLock
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.roles import SystemRole
from .base import AccountsBaseTestCase

class UserManagementAPITests(AccountsBaseTestCase):
    def setUp(self):
        # Create default roles populated in migrations (just in case they don't populate in tests)
        self.admin_role, _ = Role.objects.get_or_create(name=SystemRole.ADMIN)
        self.doctor_role, _ = Role.objects.get_or_create(name=SystemRole.DOCTOR)
        self.receptionist_role, _ = Role.objects.get_or_create(name=SystemRole.RECEPTIONIST)

        # Create Admin user
        self.admin_user = User.objects.create_user(
            email='admin_mgmt@test.com',
            password='testpassword123',
            first_name='Admin',
            last_name='User'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        # Create Doctor user (Non-admin)
        self.doctor_user = User.objects.create_user(
            email='doctor_mgmt@test.com',
            password='testpassword123',
            first_name='Doctor',
            last_name='User'
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Helper to generate JWT token and set authorization header
        self.admin_token = self._get_jwt_token(self.admin_user)
        self.doctor_token = self._get_jwt_token(self.doctor_user)

    def test_list_users_authentication_required(self):
        url = reverse('users-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_users_admin_only(self):
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_users_success_for_admin(self):
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

    def test_list_users_serializer_fields(self):
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        results = response.data['data']['results']
        self.assertTrue(len(results) > 0)
        
        # Check specific expected serializer keys
        user_data = results[0]
        expected_keys = {
            'id', 'profile_image', 'full_name', 'email', 'phone', 'phone_number', 'roles',
            'is_verified', 'is_active', 'is_locked', 'failed_login_attempts',
            'last_login', 'created_at', 'updated_at',
            'can_edit', 'can_delete', 'can_block', 'can_unlock'
        }
        self.assertEqual(set(user_data.keys()), expected_keys)
        # Ensure full_name is correctly formatted and roles is list of role names
        self.assertTrue(any(user['email'] == "admin_mgmt@test.com" and user['full_name'] == "Admin User" for user in results))
        self.assertTrue(any(user['email'] == "doctor_mgmt@test.com" and user['full_name'] == "Doctor User" for user in results))
        
        # Confirm that roles contains list of strings
        for res in results:
            self.assertTrue(isinstance(res['roles'], list))
            if res['email'] == "admin_mgmt@test.com":
                self.assertIn("ADMIN", res['roles'])
            elif res['email'] == "doctor_mgmt@test.com":
                self.assertIn("DOCTOR", res['roles'])

    def test_list_users_pagination_defaults_and_max(self):
        # Bulk create users to test pagination
        for i in range(15):
            User.objects.create_user(
                email=f'user_page_{i}@test.com',
                password='testpassword123',
                first_name='Page',
                last_name=str(i)
            )
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Default page size is 12
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['page_size'], 12)
        self.assertEqual(len(response.data['data']['results']), 12)
        self.assertEqual(response.data['data']['page'], 1)
        self.assertIsNotNone(response.data['data']['next'])
        
        # Custom page size
        response = self.client.get(url, {'page_size': 5})
        self.assertEqual(len(response.data['data']['results']), 5)
        self.assertEqual(response.data['data']['page_size'], 5)

        # Max page size is capped at 100
        response = self.client.get(url, {'page_size': 150})
        # Total active users in DB is 17 (15 + 2 from setUp)
        self.assertEqual(response.data['data']['page_size'], 100)
        self.assertEqual(len(response.data['data']['results']), 17)

    def test_list_users_pagination_validation(self):
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Non-integer page
        response = self.client.get(url, {'page': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        
        # Negative page
        response = self.client.get(url, {'page': -1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Non-integer page_size
        response = self.client.get(url, {'page_size': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Zero page_size
        response = self.client.get(url, {'page_size': 0})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_users_search(self):
        # Create users with specific details to search
        u1 = User.objects.create_user(email='kolluri@test.com', first_name='Krishna', last_name='Kolluri', phone_number='9876543210')
        u2 = User.objects.create_user(email='special@test.com', first_name='SpecialName', last_name='Smith', phone_number='1112223333')
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Search by first name
        response = self.client.get(url, {'search': 'Krishna'})
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'kolluri@test.com')
        
        # Search by last name (case-insensitive)
        response = self.client.get(url, {'search': 'kolluri'})
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'kolluri@test.com')
        
        # Search by email
        response = self.client.get(url, {'search': 'special@test.com'})
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'special@test.com')
        
        # Search by phone number
        response = self.client.get(url, {'search': '9876543210'})
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'kolluri@test.com')

    def test_list_users_role_filter(self):
        # Create user with DOCTOR role
        u1 = User.objects.create_user(email='doc1@test.com', first_name='Doc1', last_name='User')
        UserRole.objects.create(user=u1, role=self.doctor_role)
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Filter by DOCTOR
        response = self.client.get(url, {'role': 'DOCTOR'})
        # Should return self.doctor_user and u1
        self.assertEqual(response.data['data']['count'], 2)
        
        # Filter by ADMIN
        response = self.client.get(url, {'role': 'ADMIN'})
        # Should return self.admin_user
        self.assertEqual(response.data['data']['count'], 1)
        
        # Invalid role name should ignore and return empty set (count=0)
        response = self.client.get(url, {'role': 'NONEXISTENT'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 0)

    def test_list_users_active_filter(self):
        u1 = User.objects.create_user(email='inactive@test.com', first_name='Inactive', last_name='User', is_active=False)
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Filter by active=true
        response = self.client.get(url, {'is_active': 'true'})
        # u1 should not be in here
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        emails = [res['email'] for res in response.data['data']['results']]
        self.assertNotIn('inactive@test.com', emails)
        
        # Filter by active=false
        response = self.client.get(url, {'is_active': 'false'})
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'inactive@test.com')
        
        # Invalid boolean parameter should raise Validation Error
        response = self.client.get(url, {'is_active': 'invalid'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])

    def test_list_users_combined_filters(self):
        # Create active doctor
        u1 = User.objects.create_user(email='act_doc@test.com', first_name='Active', last_name='Doctor', is_active=True)
        UserRole.objects.create(user=u1, role=self.doctor_role)
        # Create inactive doctor
        u2 = User.objects.create_user(email='inact_doc@test.com', first_name='Inactive', last_name='Doctor', is_active=False)
        UserRole.objects.create(user=u2, role=self.doctor_role)
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # role=DOCTOR & is_active=true
        response = self.client.get(url, {'role': 'DOCTOR', 'is_active': 'true'})
        # Should include self.doctor_user and u1 (2 active doctors)
        self.assertEqual(response.data['data']['count'], 2)
        emails = [res['email'] for res in response.data['data']['results']]
        self.assertIn('act_doc@test.com', emails)
        self.assertNotIn('inact_doc@test.com', emails)

    def test_list_users_multiple_roles(self):
        # Create user with both DOCTOR and RECEPTIONIST roles
        u1 = User.objects.create_user(email='multi@test.com', first_name='Multi', last_name='Role')
        UserRole.objects.create(user=u1, role=self.doctor_role)
        UserRole.objects.create(user=u1, role=self.receptionist_role)
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Search by email
        response = self.client.get(url, {'search': 'multi@test.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        user_roles = response.data['data']['results'][0]['roles']
        self.assertEqual(set(user_roles), {'DOCTOR', 'RECEPTIONIST'})

    def test_list_users_ordering(self):
        from django.utils import timezone
        from datetime import timedelta
        # Make setUp users older than u1 and u2 so u1 and u2 are the two newest users
        User.objects.filter(email__in=['admin_mgmt@test.com', 'doctor_mgmt@test.com']).update(
            created_at=timezone.now() - timedelta(days=10)
        )

        # Create users sequentially
        u1 = User.objects.create_user(email='first@test.com', first_name='First', last_name='User')
        u2 = User.objects.create_user(email='second@test.com', first_name='Second', last_name='User')
        
        # Set created_at explicitly (via update to bypass auto_now_add on save)
        User.objects.filter(id=u1.id).update(created_at=timezone.now() - timedelta(days=1))
        User.objects.filter(id=u2.id).update(created_at=timezone.now())
        
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(url, {'page_size': 2})
        results = response.data['data']['results']
        
        # Newest users should be first: u2 should be before u1
        self.assertEqual(results[0]['email'], 'second@test.com')
        self.assertEqual(results[1]['email'], 'first@test.com')

    def test_create_user_admin_only(self):
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "password": "SecurePassword@123",
            "roles": ["ADMIN"]
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_user_success_admin_roles(self):
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "phone_number": "9876543210",
            "password": "SecurePassword@123",
            "roles": ["ADMIN", "DOCTOR"],
            "is_active": True,
            "is_verified": False
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "User created successfully.")
        
        user_data = response.data['data']
        self.assertEqual(user_data['first_name'], "Krishna")
        self.assertEqual(user_data['last_name'], "Kolluri")
        self.assertEqual(user_data['full_name'], "Krishna Kolluri")
        self.assertEqual(user_data['email'], "krishna@gmail.com")
        self.assertEqual(user_data['phone_number'], "9876543210")
        self.assertEqual(set(user_data['roles']), {"ADMIN", "DOCTOR"})
        self.assertTrue(user_data['is_active'])
        self.assertFalse(user_data['is_verified'])
        self.assertNotIn('password', user_data)
        self.assertNotIn('is_staff', user_data)
        self.assertNotIn('is_superuser', user_data)

        # Verify DB states
        new_user = User.objects.get(email="krishna@gmail.com")
        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(new_user.check_password("SecurePassword@123"))

        # Verify Activity Log
        from apps.accounts.constants.activity_types import ActivityType
        log = ActivityLog.objects.filter(action=ActivityType.USER_CREATED, user=self.admin_user).first()
        self.assertIsNotNone(log)
        self.assertIn("Admin admin_mgmt@test.com created user krishna@gmail.com.", log.description)

    def test_create_user_duplicate_email(self):
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "doctor_mgmt@test.com", # already exists in setUp
            "password": "SecurePassword@123",
            "roles": ["DOCTOR"]
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Validation failed.")
        self.assertIn("email", response.data['errors'])
        self.assertEqual(response.data['errors']['email'][0], "User with this email already exists.")

    def test_create_user_duplicate_phone(self):
        # First create a user with a specific phone number
        User.objects.create_user(
            email="phone_user@test.com",
            password="testpassword123",
            phone_number="9876543210"
        )
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "phone_number": "9876543210", # duplicate
            "password": "SecurePassword@123",
            "roles": ["DOCTOR"]
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data['errors'])
        self.assertEqual(response.data['errors']['phone_number'][0], "User with this phone number already exists.")

    def test_create_user_missing_required_fields(self):
        url = reverse('users-list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        
        # Missing first_name
        data = {
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "password": "SecurePassword@123",
            "roles": ["DOCTOR"]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("first_name", response.data['errors'])

        # Missing last_name
        data = {
            "first_name": "Krishna",
            "email": "krishna@gmail.com",
            "password": "SecurePassword@123",
            "roles": ["DOCTOR"]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("last_name", response.data['errors'])

        # Missing password
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "roles": ["DOCTOR"]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data['errors'])

    def test_create_user_weak_password(self):
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "password": "123", # weak
            "roles": ["DOCTOR"]
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("password", response.data['errors'])

    def test_create_user_invalid_role(self):
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "password": "SecurePassword@123",
            "roles": ["MANAGER"] # invalid
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", response.data['errors'])
        self.assertEqual(response.data['errors']['roles'][0], "Invalid role: MANAGER")

    def test_create_user_empty_roles(self):
        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "password": "SecurePassword@123",
            "roles": [] # empty
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", response.data['errors'])

    def test_create_user_with_profile_image(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from django.test import override_settings
        from PIL import Image
        import tempfile
        
        # Generate dummy image in memory
        image = Image.new('RGB', (100, 100))
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        image.save(tmp_file, 'JPEG')
        tmp_file.seek(0)
        
        uploaded_image = SimpleUploadedFile(
            name='test_profile.jpg',
            content=tmp_file.read(),
            content_type='image/jpeg'
        )

        url = reverse('users-list')
        data = {
            "first_name": "Krishna",
            "last_name": "Kolluri",
            "email": "krishna@gmail.com",
            "password": "SecurePassword@123",
            "roles": ["DOCTOR"],
            "profile_image": uploaded_image
        }
        
        with override_settings(MEDIA_ROOT=tempfile.gettempdir()):
            self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
            response = self.client.post(url, data, format='multipart')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            user_data = response.data['data']
            self.assertIsNotNone(user_data['profile_image'])
            self.assertTrue(user_data['profile_image'].startswith("http"))

    def test_retrieve_user_success_for_admin(self):
        url = reverse('users-detail', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        user_data = response.data['data']
        self.assertEqual(user_data['id'], str(self.doctor_user.id))
        self.assertEqual(user_data['email'], self.doctor_user.email)
        self.assertEqual(user_data['first_name'], self.doctor_user.first_name)
        self.assertEqual(user_data['last_name'], self.doctor_user.last_name)
        self.assertEqual(user_data['roles'], ['DOCTOR'])
        self.assertFalse(user_data['locked'])

    def test_retrieve_user_forbidden_for_non_admin(self):
        url = reverse('users-detail', args=[self.admin_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_user_not_found(self):
        url = reverse('users-detail', args=[99999])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_success_for_admin(self):
        url = reverse('users-detail', args=[self.doctor_user.id])
        data = {
            "first_name": "UpdatedDoc",
            "last_name": "LastName",
            "email": "updated_doc@test.com",
            "phone_number": "1122334455",
            "roles": ["DOCTOR", "RECEPTIONIST"],
            "is_active": True,
            "is_verified": True
        }
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        user_data = response.data['data']
        self.assertEqual(user_data['first_name'], "UpdatedDoc")
        self.assertEqual(user_data['last_name'], "LastName")
        self.assertEqual(user_data['email'], "updated_doc@test.com")
        self.assertEqual(user_data['phone_number'], "1122334455")
        self.assertEqual(set(user_data['roles']), {"DOCTOR", "RECEPTIONIST"})
        self.assertTrue(user_data['active'])
        self.assertTrue(user_data['verified'])

        # Verify DB changes
        self.doctor_user.refresh_from_db()
        self.assertEqual(self.doctor_user.first_name, "UpdatedDoc")
        self.assertEqual(self.doctor_user.email, "updated_doc@test.com")

        # Verify activity log
        log = ActivityLog.objects.filter(action='USER_UPDATED', user=self.admin_user).first()
        self.assertIsNotNone(log)
        self.assertIn("updated_doc@test.com", log.description)

    def test_update_user_duplicate_email(self):
        # Create another user to clash with
        User.objects.create_user(email="clash_email@test.com", password="testpassword123")
        
        url = reverse('users-detail', args=[self.doctor_user.id])
        data = {"email": "clash_email@test.com"}
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("email", response.data['errors'])

    def test_update_user_duplicate_phone(self):
        # Create another user with a phone number to clash with
        User.objects.create_user(email="phone_clash@test.com", password="testpassword123", phone_number="5555555555")
        
        url = reverse('users-detail', args=[self.doctor_user.id])
        data = {"phone_number": "5555555555"}
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("phone_number", response.data['errors'])

    def test_update_user_invalid_role(self):
        url = reverse('users-detail', args=[self.doctor_user.id])
        data = {"roles": ["INVALID_ROLE"]}
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("roles", response.data['errors'])

    def test_lock_user_success(self):
        url = reverse('users-lock', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify db locks
        self.assertTrue(self.doctor_user.locks.filter(is_active=True).exists())
        
        # Verify activity log
        log = ActivityLog.objects.filter(action='USER_LOCKED', user=self.admin_user).first()
        self.assertIsNotNone(log)
        self.assertIn(self.doctor_user.email, log.description)

    def test_lock_user_already_locked(self):
        # Lock first
        url = reverse('users-lock', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Lock again
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "User account is already locked.")

    def test_unlock_user_success(self):
        # Lock the account first
        from apps.accounts.services.user_service import UserService
        UserService.lock_user(self.doctor_user, self.admin_user)
        self.assertTrue(self.doctor_user.locks.filter(is_active=True).exists())
        
        # Call unlock
        url = reverse('users-unlock', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        
        # Verify unlocked
        self.doctor_user.refresh_from_db()
        self.assertFalse(self.doctor_user.locks.filter(is_active=True).exists())

        # Verify activity logs
        log_admin = ActivityLog.objects.filter(action='USER_UNLOCKED', user=self.admin_user).first()
        log_user = ActivityLog.objects.filter(action='ACCOUNT_UNLOCKED', user=self.doctor_user).first()
        self.assertIsNotNone(log_admin)
        self.assertIsNotNone(log_user)

    def test_unlock_user_not_locked(self):
        url = reverse('users-unlock', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "User account is not locked.")

    def test_delete_user_success(self):
        url = reverse('users-detail', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])

        # Verify deleted
        self.assertFalse(User.objects.filter(id=self.doctor_user.id).exists())

        # Verify activity log
        log = ActivityLog.objects.filter(action='USER_DELETED', user=self.admin_user).first()
        self.assertIsNotNone(log)
        self.assertIn(self.doctor_user.email, log.description)

    def test_delete_user_cannot_delete_self(self):
        url = reverse('users-detail', args=[self.admin_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Administrators cannot delete their own account.")

    def test_delete_user_cannot_delete_superuser(self):
        # Make another user superuser
        super_user = User.objects.create_superuser(email="super@test.com", password="testpassword123")
        url = reverse('users-detail', args=[super_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertEqual(response.data['message'], "Superusers cannot be deleted.")

    def test_users_filtering_and_pagination(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        # Test search filter
        url = reverse('users-list')
        response = self.client.get(url, {'search': 'Doctor'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'doctor_mgmt@test.com')

        # Test role filter
        response = self.client.get(url, {'role': 'ADMIN'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['count'], 1)
        self.assertEqual(response.data['data']['results'][0]['email'], 'admin_mgmt@test.com')

        # Test status filter
        response = self.client.get(url, {'is_active': 'true'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Both admin and doctor are active
        self.assertEqual(response.data['data']['count'], 2)

    def test_statistics_permission_checks(self):
        url = reverse('users-statistics')
        # Unauthenticated
        self.client.credentials()
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        # Non-admin Doctor
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.doctor_token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_statistics_calculations(self):
        # Clear the database for users to start fresh and calculate precisely
        User.objects.all().delete()
        
        # Create 5 users:
        # 1. Admin (Active, Verified)
        admin = User.objects.create_user(email='admin_stat@test.com', first_name='A', is_active=True, is_verified=True)
        UserRole.objects.create(user=admin, role=self.admin_role)
        
        # 2. Doctor (Active, Verified)
        doc = User.objects.create_user(email='doc_stat@test.com', first_name='D', is_active=True, is_verified=True)
        UserRole.objects.create(user=doc, role=self.doctor_role)
        
        # 3. Doctor (Active, Unverified)
        doc2 = User.objects.create_user(email='doc_stat2@test.com', first_name='D2', is_active=True, is_verified=False)
        UserRole.objects.create(user=doc2, role=self.doctor_role)
        
        # 4. Receptionist (Inactive, Verified)
        rec = User.objects.create_user(email='rec_stat@test.com', first_name='R', is_active=False, is_verified=True)
        UserRole.objects.create(user=rec, role=self.receptionist_role)
        
        # 5. User (Inactive, Unverified)
        User.objects.create_user(email='user_stat@test.com', first_name='U', is_active=False, is_verified=False)
        
        # Stats expected:
        # Total: 5
        # Active: 3 (admin, doc, doc2)
        # Inactive: 2 (rec, user)
        # Verified: 3 (admin, doc, rec)
        
        admin_token = self._get_jwt_token(admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        url = reverse('users-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['message'], "User statistics retrieved successfully.")
        
        data = response.data['data']
        self.assertEqual(data['total_users'], 5)
        self.assertEqual(data['active_users'], 3)
        self.assertEqual(data['inactive_users'], 2)
        self.assertEqual(data['verified_users'], 3)

    def test_statistics_zero_users(self):
        # We need at least 1 Admin user to authenticate and call the endpoint.
        User.objects.all().delete()
        admin = User.objects.create_user(email='admin_zero@test.com', first_name='A', is_active=True, is_verified=True)
        UserRole.objects.create(user=admin, role=self.admin_role)
        
        admin_token = self._get_jwt_token(admin)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {admin_token}')
        
        url = reverse('users-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.data['data']
        self.assertEqual(data['total_users'], 1)
        self.assertEqual(data['active_users'], 1)
        self.assertEqual(data['inactive_users'], 0)
        self.assertEqual(data['verified_users'], 1)
