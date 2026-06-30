from django.db import migrations

def seed_data(apps, schema_editor):
    Permission = apps.get_model('accounts', 'Permission')
    Role = apps.get_model('accounts', 'Role')

    # 1. Create Permissions
    permissions_to_create = [
        # User Management
        {"name": "View Users", "code": "view_users", "group": "User Management", "description": "Can view user accounts"},
        {"name": "Manage Users", "code": "manage_users", "group": "User Management", "description": "Can create, update, and delete user accounts"},
        # Role Management
        {"name": "View Roles", "code": "view_roles", "group": "Role Management", "description": "Can view roles and permissions"},
        {"name": "Manage Roles", "code": "manage_roles", "group": "Role Management", "description": "Can create, update, and delete roles"},
        # Patient Management
        {"name": "View Patients", "code": "view_patients", "group": "Patient Management", "description": "Can view patient records"},
        {"name": "Manage Patients", "code": "manage_patients", "group": "Patient Management", "description": "Can create and update patient records"},
        # Consultation Management
        {"name": "View Consultations", "code": "view_consultations", "group": "Consultation Management", "description": "Can view consultations"},
        {"name": "Manage Consultations", "code": "manage_consultations", "group": "Consultation Management", "description": "Can book and manage consultations"},
        # Security Audit
        {"name": "View Security Logs", "code": "view_security_logs", "group": "Security Audit", "description": "Can view security audit logs"},
    ]

    created_permissions = {}
    for perm_data in permissions_to_create:
        perm, _ = Permission.objects.get_or_create(
            code=perm_data["code"],
            defaults={
                "name": perm_data["name"],
                "group": perm_data["group"],
                "description": perm_data["description"]
            }
        )
        created_permissions[perm.code] = perm

    # 2. Create/Update System Roles
    admin_role, _ = Role.objects.get_or_create(
        name="ADMIN",
        defaults={"description": "System Administrator with full access", "is_system": True, "is_active": True}
    )
    admin_role.is_system = True
    admin_role.is_active = True
    admin_role.save()

    doctor_role, _ = Role.objects.get_or_create(
        name="DOCTOR",
        defaults={"description": "Medical Doctor with clinical access", "is_system": True, "is_active": True}
    )
    doctor_role.is_system = True
    doctor_role.is_active = True
    doctor_role.save()

    receptionist_role, _ = Role.objects.get_or_create(
        name="RECEPTIONIST",
        defaults={"description": "Receptionist with scheduling access", "is_system": True, "is_active": True}
    )
    receptionist_role.is_system = True
    receptionist_role.is_active = True
    receptionist_role.save()

    # 3. Associate Permissions
    # ADMIN gets all permissions
    admin_role.permissions.set(list(created_permissions.values()))

    # DOCTOR gets specific clinical and scheduling permissions
    doctor_perms = [
        created_permissions["view_users"],
        created_permissions["view_patients"],
        created_permissions["manage_patients"],
        created_permissions["view_consultations"],
        created_permissions["manage_consultations"],
    ]
    doctor_role.permissions.set(doctor_perms)

    # RECEPTIONIST gets scheduling and view permissions
    receptionist_perms = [
        created_permissions["view_users"],
        created_permissions["view_patients"],
        created_permissions["view_consultations"],
        created_permissions["manage_consultations"],
    ]
    receptionist_role.permissions.set(receptionist_perms)

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0015_permission_alter_role_options_role_created_by_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_data),
    ]
