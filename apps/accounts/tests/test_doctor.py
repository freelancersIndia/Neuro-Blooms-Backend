from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from apps.accounts.models.user import User, Role, UserRole

class DoctorAPITests(APITestCase):
    def setUp(self):
        super().setUp()
        self.admin_role, _ = Role.objects.get_or_create(name='ADMIN')
        self.doctor_role, _ = Role.objects.get_or_create(name='DOCTOR')

        # Create Admin
        self.admin_user = User.objects.create_user(
            email='admin_test@test.com', password='testpassword123', first_name='Admin'
        )
        UserRole.objects.create(user=self.admin_user, role=self.admin_role)

        # Create Doctor
        self.doctor_user = User.objects.create_user(
            email='doctor_test@test.com', password='testpassword123', 
            first_name='Doctor', last_name='Who', 
            specialization='Cardiology', qualification='MD', experience=10
        )
        UserRole.objects.create(user=self.doctor_user, role=self.doctor_role)

        # Create a non-doctor user
        self.normal_user = User.objects.create_user(
            email='normal_test@test.com', password='testpassword123', first_name='Normal'
        )

        from rest_framework_simplejwt.tokens import RefreshToken
        self.token = str(RefreshToken.for_user(self.doctor_user).access_token)

    def test_get_all_doctors_unauthenticated(self):
        url = reverse('doctor_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        data = response.data['data']
        self.assertEqual(len(data), 1)
        self.assertNotIn('email', data[0])

    def test_get_all_doctors_success(self):
        url = reverse('doctor_list')
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        data = response.data['data']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['email'], 'doctor_test@test.com')
        self.assertEqual(data[0]['full_name'], 'Doctor Who')
        self.assertEqual(data[0]['specialization'], 'Cardiology')

    def test_get_doctor_detail_success(self):
        url = reverse('doctor_detail', args=[self.doctor_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        data = response.data['data']
        self.assertEqual(data['email'], 'doctor_test@test.com')
        self.assertEqual(data['specialization'], 'Cardiology')
        self.assertIsNotNone(data['availability'])
        self.assertEqual(data['availability']['consultation_duration'], 30)

    def test_get_doctor_detail_not_found(self):
        url = reverse('doctor_detail', args=[self.normal_user.id])
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
