from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from apps.accounts.models.user import Role, UserRole
from apps.accounts.constants.roles import SystemRole

User = get_user_model()

class AccountsBaseTestCase(APITestCase):
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

    def _get_jwt_token(self, user):
        from rest_framework_simplejwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)
        return str(refresh.access_token)
