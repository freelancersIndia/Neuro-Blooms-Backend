import os
from django.core.management.base import BaseCommand, CommandError
from apps.accounts.models.user import User, Role, UserRole
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class Command(BaseCommand):
    help = 'Creates the initial administrator user from environment variables.'

    def handle(self, *args, **options):
        raw_email = os.environ.get('INITIAL_ADMIN_EMAIL')
        raw_password = os.environ.get('INITIAL_ADMIN_PASSWORD')
        raw_first_name = os.environ.get('INITIAL_ADMIN_FIRST_NAME', 'Admin')
        raw_last_name = os.environ.get('INITIAL_ADMIN_LAST_NAME', 'User')

        if not raw_email or not raw_password:
            raise CommandError(
                "INITIAL_ADMIN_EMAIL and INITIAL_ADMIN_PASSWORD environment variables must be set in .env."
            )

        # Defensive cleaning of environment variables to remove any parsed quotes
        email = raw_email.strip().strip('"').strip("'")
        password = raw_password.strip().strip('"').strip("'")
        first_name = raw_first_name.strip().strip('"').strip("'")
        last_name = raw_last_name.strip().strip('"').strip("'")

        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.WARNING(f"User with email '{email}' already exists. No actions taken."))
            return

        # Get or create ADMIN role
        admin_role, _ = Role.objects.get_or_create(
            name='ADMIN',
            defaults={'description': 'System Administrator with full access.'}
        )

        # Create user
        user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            is_active=True,
            is_verified=True,
            is_staff=True,
            is_superuser=True
        )

        # Assign ADMIN role
        UserRole.objects.get_or_create(user=user, role=admin_role)

        # Log initial admin creation activity
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.INITIAL_ADMIN_CREATED,
            description=f"Initial administrator account created for {email}."
        )

        self.stdout.write(self.style.SUCCESS(f"Successfully created initial admin: {email}"))
