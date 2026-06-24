from django.core.management.base import BaseCommand
from apps.accounts.models.user import Role
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class Command(BaseCommand):
    help = 'Seeds system roles (ADMIN, DOCTOR, RECEPTIONIST) into the database.'

    def handle(self, *args, **options):
        roles_to_seed = [
            ('ADMIN', 'System Administrator with full access.'),
            ('DOCTOR', 'Medical doctor with patient and clinical access.'),
            ('RECEPTIONIST', 'Receptionist with appointment and scheduling access.')
        ]
        
        seeded_roles = []
        for name, desc in roles_to_seed:
            role, created = Role.objects.get_or_create(
                name=name,
                defaults={'description': desc}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created role: {name}"))
                seeded_roles.append(name)
            else:
                self.stdout.write(self.style.WARNING(f"Role already exists: {name}"))

        if seeded_roles:
            ActivityLog.objects.create(
                user=None,
                action=ActivityType.ROLE_SEEDED,
                description=f"System roles seeded: {', '.join(seeded_roles)}."
            )
