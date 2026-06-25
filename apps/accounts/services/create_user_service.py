from django.db import transaction
from django.contrib.auth import get_user_model
from apps.accounts.models.user import Role, UserRole
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class CreateUserService:
    @staticmethod
    @transaction.atomic
    def create_user(
        first_name: str,
        last_name: str,
        email: str,
        password: str,
        roles: list,
        phone_number: str = None,
        profile_image = None,
        is_active: bool = True,
        is_verified: bool = False,
        admin_user = None,
        ip_address: str = None
    ) -> User:
        """
        Creates a new user, hashes the password, assigns roles, saves profile image,
        and logs the activity log.
        """
        # Set is_staff=True, is_superuser=False
        user = User(
            email=email.lower().strip(),
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            phone_number=phone_number,
            profile_image=profile_image,
            is_active=is_active,
            is_verified=is_verified,
            is_staff=True,
            is_superuser=False
        )
        user.set_password(password)
        user.save()

        # Fetch and assign roles
        for role_name in roles:
            role = Role.objects.get(name=role_name.upper())
            UserRole.objects.create(user=user, role=role)

        # Log Activity
        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            action=ActivityType.USER_CREATED,
            description=f"Admin {admin_email} created user {user.email}.",
            ip_address=ip_address
        )

        return user
