from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import User, Role, UserRole, Permission

class RoleManagementTestCase(APITestCase):
    def setUp(self):
        super().setUp()
        # We need an admin user for these endpoints
        self.admin_user = User.objects.create_user(
            email='admin_role_test@test.com',
            password='testpassword123',
            first_name='Admin',
            last_name='User'
        )
        self.admin_role = Role.objects.get(name='ADMIN')
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        from rest_framework_simplejwt.tokens import RefreshToken
        self.admin_token = str(RefreshToken.for_user(self.admin_user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.admin_token}')

        # Create a custom role
        self.custom_role = Role.objects.create(
            name='Nurse',
            description='Nurse duties',
            is_system=False,
            is_active=True
        )
        self.nurse_user = User.objects.create_user(
            email='nurse@test.com',
            password='testpassword123',
            first_name='Nurse',
            last_name='One'
        )
        UserRole.objects.create(user=self.nurse_user, role=self.custom_role)

    def test_list_roles_success(self):
        url = reverse('roles-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        # Check results are present
        self.assertIn('results', response.data['data'])
        results = response.data['data']['results']
        # We should have at least the seeded roles + Nurse
        self.assertTrue(len(results) >= 4)

    def test_list_roles_filtering_and_search(self):
        url = reverse('roles-list')
        
        # Test Search
        response = self.client.get(f"{url}?search=Nurse")
        self.assertEqual(len(response.data['data']['results']), 1)
        self.assertEqual(response.data['data']['results'][0]['name'], 'Nurse')

        # Test Filter Type Custom
        response = self.client.get(f"{url}?type=custom")
        self.assertEqual(len(response.data['data']['results']), 1)

        # Test Filter Type System
        response = self.client.get(f"{url}?type=system")
        self.assertTrue(len(response.data['data']['results']) >= 3)

    def test_role_statistics(self):
        url = reverse('roles-statistics')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        stats = response.data['data']
        self.assertEqual(stats['total_roles'], Role.objects.filter(is_deleted=False).count())
        self.assertEqual(stats['custom_roles'], 1)
        self.assertTrue(stats['system_roles'] >= 3)

    def test_role_detail(self):
        url = reverse('roles-detail', args=[self.custom_role.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        data = response.data['data']
        self.assertEqual(data['name'], 'Nurse')
        self.assertIn('permissions', data)
        self.assertIn('assigned_users', data)
        self.assertEqual(data['assigned_users']['count'], 1)
        self.assertEqual(data['assigned_users']['results'][0]['email'], 'nurse@test.com')

    def test_create_role_valid(self):
        url = reverse('roles-list')
        perm = Permission.objects.first()
        data = {
            'name': 'Pharmacist',
            'description': 'Pharmacy management',
            'is_active': True,
            'permissions': [str(perm.id)]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])
        self.assertEqual(response.data['data']['name'], 'Pharmacist')

    def test_create_role_duplicate_name(self):
        url = reverse('roles-list')
        perm = Permission.objects.first()
        data = {
            'name': 'Nurse', # already exists
            'description': 'Duplicate nurse',
            'permissions': [str(perm.id)]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['success'])
        self.assertIn('name', response.data['errors'])

    def test_create_role_empty_permissions(self):
        url = reverse('roles-list')
        data = {
            'name': 'Pharmacist 2',
            'description': 'No permissions',
            'permissions': []
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_system_role_name_fails(self):
        url = reverse('roles-detail', args=[self.admin_role.id])
        data = {
            'name': 'SUPER_ADMIN_CHANGED'
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_system_role_fails(self):
        url = reverse('roles-detail', args=[self.admin_role.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('system', response.data['message'].lower())

    def test_delete_role_with_users_fails(self):
        url = reverse('roles-detail', args=[self.custom_role.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('assigned users', response.data['message'].lower())

    def test_delete_role_success_soft_delete(self):
        # Create a temporary custom role with no users
        temp_role = Role.objects.create(name='TempRole', is_system=False, is_active=True)
        url = reverse('roles-detail', args=[temp_role.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify soft delete
        temp_role.refresh_from_db()
        self.assertTrue(temp_role.is_deleted)
        
        # Verify it doesn't show up in list queryset
        list_url = reverse('roles-list')
        response_list = self.client.get(list_url)
        role_ids = [r['id'] for r in response_list.data['data']['results']]
        self.assertNotIn(str(temp_role.id), role_ids)

    def test_assign_remove_permissions(self):
        # Assign permission
        url_assign = reverse('roles-assign-permissions', args=[self.custom_role.id])
        perm = Permission.objects.all()[0]
        response = self.client.post(url_assign, {'permission_ids': [str(perm.id)]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.custom_role.permissions.filter(id=perm.id).exists())

        # Remove permission
        url_remove = reverse('roles-remove-permissions', args=[self.custom_role.id])
        response = self.client.post(url_remove, {'permission_ids': [str(perm.id)]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(self.custom_role.permissions.filter(id=perm.id).exists())

    def test_assign_remove_users(self):
        # Create a new user
        new_user = User.objects.create_user(
            email='new_user_test@test.com',
            password='testpassword123',
            first_name='New',
            last_name='User'
        )
        
        # Assign user
        url_assign = reverse('roles-assign-users', args=[self.custom_role.id])
        response = self.client.post(url_assign, {'user_ids': [str(new_user.id)]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(new_user.user_roles.filter(role=self.custom_role).exists())

        # Remove user
        url_remove = reverse('roles-remove-users', args=[self.custom_role.id])
        response = self.client.post(url_remove, {'user_ids': [str(new_user.id)]}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(new_user.user_roles.filter(role=self.custom_role).exists())
