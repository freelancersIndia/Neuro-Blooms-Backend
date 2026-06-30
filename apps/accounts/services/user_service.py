from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound

from apps.accounts.models.user import User, Role, UserRole, AccountLock, FailedLoginAttempt
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.selectors.user import get_user_by_id
from apps.accounts.services.session_service import SessionService

class UserService:
    @staticmethod
    def get_user_details(user_id) -> User:
        """
        Retrieves user details. Raises NotFound exception if user does not exist.
        """
        user = get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found.")
        return user

    @staticmethod
    @transaction.atomic
    def update_user(
        user_id,
        first_name=None,
        last_name=None,
        email=None,
        phone_number=None,
        profile_image=None,
        roles=None,
        is_active=None,
        is_verified=None,
        admin_user=None,
        ip_address=None
    ) -> User:
        """
        Updates an existing user's details and role assignments.
        """
        user = get_user_id = get_user_by_id(user_id)
        if not user:
            raise NotFound("User not found.")

        updated_fields = []

        # Validate unique email
        if email is not None:
            email_lower = email.lower().strip()
            if user.email != email_lower:
                if User.objects.filter(email__iexact=email_lower).exclude(id=user.id).exists():
                    raise ValidationError({"email": ["User with this email already exists."]})
                user.email = email_lower
                updated_fields.append('email')

        # Validate unique phone number
        if phone_number is not None:
            if phone_number == '':
                phone_number = None
            if user.phone_number != phone_number:
                if phone_number and User.objects.filter(phone_number=phone_number).exclude(id=user.id).exists():
                    raise ValidationError({"phone_number": ["User with this phone number already exists."]})
                user.phone_number = phone_number
                updated_fields.append('phone_number')

        if first_name is not None:
            first_name_stripped = first_name.strip()
            if user.first_name != first_name_stripped:
                user.first_name = first_name_stripped
                updated_fields.append('first_name')

        if last_name is not None:
            last_name_stripped = last_name.strip()
            if user.last_name != last_name_stripped:
                user.last_name = last_name_stripped
                updated_fields.append('last_name')

        if profile_image is not None:
            user.profile_image = profile_image
            updated_fields.append('profile_image')

        if is_active is not None:
            if user.is_active != is_active:
                if not is_active:
                    # Validation: Cannot deactivate yourself
                    if admin_user and user.id == admin_user.id:
                        raise ValidationError({"is_active": ["Cannot deactivate yourself."]})
                    # Validation: Cannot deactivate the final Super Admin
                    if user.is_superuser:
                        active_superusers_count = User.objects.filter(is_superuser=True, is_active=True, is_deleted=False).count()
                        if active_superusers_count <= 1:
                            raise ValidationError({"is_active": ["Cannot deactivate the final Super Admin."]})
                    # Validation: Cannot deactivate the final administrator (ADMIN role)
                    if user.has_role('ADMIN'):
                        active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
                        if active_admins_count <= 1:
                            raise ValidationError({"is_active": ["Cannot deactivate the final administrator."]})

                user.is_active = is_active
                updated_fields.append('is_active')

        if is_verified is not None:
            if user.is_verified != is_verified:
                user.is_verified = is_verified
                updated_fields.append('is_verified')

        if admin_user:
            user.updated_by = admin_user

        user.save()

        # Update Roles
        if roles is not None:
            normalized_roles = [r.upper() for r in roles]
            if len(normalized_roles) != len(set(normalized_roles)):
                raise ValidationError({"roles": ["Duplicate roles are not allowed."]})
            
            for role_name in normalized_roles:
                if not Role.objects.filter(name=role_name).exists():
                    raise ValidationError({"roles": [f"Invalid role: {role_name}"]})

            # Check if we are removing the last ADMIN role from the final administrator
            if user.has_role('ADMIN') and 'ADMIN' not in normalized_roles:
                active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
                if active_admins_count <= 1:
                    raise ValidationError({"roles": ["Cannot remove the last ADMIN role from the final administrator."]})

            existing_roles = [r.name for r in user.roles.all()]
            if set(existing_roles) != set(normalized_roles):
                # Calculate what was added and removed for audit logs
                added_roles = set(normalized_roles) - set(existing_roles)
                removed_roles = set(existing_roles) - set(normalized_roles)

                UserRole.objects.filter(user=user).delete()
                for role_name in normalized_roles:
                    role = Role.objects.get(name=role_name)
                    UserRole.objects.create(user=user, role=role)
                updated_fields.append('roles')

                for r in added_roles:
                    ActivityLog.objects.create(
                        user=admin_user,
                        target_user=user,
                        action=ActivityType.ROLE_ASSIGNED,
                        description=f"Admin {admin_user.email if admin_user else 'System'} assigned role {r} to user {user.email}.",
                        ip_address=ip_address
                    )
                for r in removed_roles:
                    ActivityLog.objects.create(
                        user=admin_user,
                        target_user=user,
                        action=ActivityType.ROLE_REMOVED,
                        description=f"Admin {admin_user.email if admin_user else 'System'} removed role {r} from user {user.email}.",
                        ip_address=ip_address
                    )

        # Log administrative action
        if updated_fields:
            admin_email = admin_user.email if admin_user else "System"
            ActivityLog.objects.create(
                user=admin_user,
                target_user=user,
                action=ActivityType.USER_UPDATED,
                description=f"Admin {admin_email} updated user {user.email}. Updated fields: {', '.join(updated_fields)}.",
                ip_address=ip_address
            )

        return user

    @staticmethod
    @transaction.atomic
    def block_user(user, admin_user=None, ip_address=None, reason="Manual block by administrator") -> None:
        """
        Manually blocks a user account.
        """
        if admin_user and user.id == admin_user.id:
            raise ValidationError("Cannot block yourself.")

        # Check if already blocked or locked
        now = timezone.now()
        active_lock = user.locks.filter(is_active=True, unlock_at__gt=now).first()
        if user.is_blocked or active_lock:
            raise ValidationError("User account is already locked.")

        # Validation: Cannot block the final Super Admin
        if user.is_superuser:
            active_superusers_count = User.objects.filter(is_superuser=True, is_active=True, is_deleted=False).count()
            if active_superusers_count <= 1:
                raise ValidationError("Cannot block the final Super Admin.")

        # Validation: Cannot block the final administrator (ADMIN role)
        if user.has_role('ADMIN'):
            active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
            if active_admins_count <= 1:
                raise ValidationError("Cannot block the final administrator.")

        user.is_blocked = True
        if admin_user:
            user.updated_by = admin_user
        user.save()

        # Also create a permanent account lock record for audit/security purposes
        unlock_at = now + timezone.timedelta(days=365 * 99)
        AccountLock.objects.create(
            user=user,
            unlock_at=unlock_at,
            reason=reason,
            is_active=True
        )

        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            target_user=user,
            action=ActivityType.USER_LOCKED,
            description=f"Admin {admin_email} blocked user {user.email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def lock_user(user, admin_user=None, ip_address=None, reason="Manual lock by administrator") -> None:
        """
        Manually locks a user account. (Backwards compatibility)
        """
        UserService.block_user(user, admin_user, ip_address, reason)

    @staticmethod
    @transaction.atomic
    def unlock_user(user, admin_user=None, ip_address=None) -> None:
        """
        Manually unlocks a user account, deactivating active locks, manual blocks, and resetting failed login attempts.
        """
        now = timezone.now()
        active_locks = user.locks.filter(is_active=True, unlock_at__gt=now)
        is_currently_blocked = user.is_blocked

        if not active_locks.exists() and not is_currently_blocked:
            raise ValidationError("User account is not locked.")

        user.is_blocked = False
        if admin_user:
            user.updated_by = admin_user
        user.save()

        active_locks.update(is_active=False)

        # Reset failed attempts
        FailedLoginAttempt.objects.filter(email=user.email).delete()

        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            target_user=user,
            action=ActivityType.USER_UNLOCKED,
            description=f"Admin {admin_email} unlocked user {user.email}.",
            ip_address=ip_address
        )

        # Legacy log for backwards compatibility and test verification
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.ACCOUNT_UNLOCKED,
            description=f"Account unlocked by administrator {admin_email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def delete_user(user, admin_user, ip_address=None) -> None:
        """
        Soft deletes a user account, verifying self-deletion and superuser constraints.
        """
        if user.id == admin_user.id:
            raise ValidationError("Administrators cannot delete their own account.")

        if user.is_superuser:
            raise ValidationError("Superusers cannot be deleted.")

        email = user.email
        user.is_deleted = True
        user.is_active = False
        user.updated_by = admin_user
        user.save()

        # Deactivate all active sessions for security
        SessionService.deactivate_all_sessions(user)

        # Log activity
        admin_email = admin_user.email
        ActivityLog.objects.create(
            user=admin_user,
            target_user=user,
            action=ActivityType.USER_DELETED,
            description=f"Admin {admin_email} deleted user {email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def activate_user(user, admin_user=None, ip_address=None) -> None:
        """
        Activates a deactivated user.
        """
        if user.is_active:
            raise ValidationError("User is already active.")

        user.is_active = True
        if admin_user:
            user.updated_by = admin_user
        user.save()

        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            target_user=user,
            action=ActivityType.USER_UPDATED,
            description=f"Admin {admin_email} activated user {user.email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def deactivate_user(user, admin_user=None, ip_address=None) -> None:
        """
        Deactivates a user.
        """
        if admin_user and user.id == admin_user.id:
            raise ValidationError("Cannot deactivate yourself.")

        if not user.is_active:
            raise ValidationError("User is already inactive.")

        # Validation: Cannot deactivate the final Super Admin
        if user.is_superuser:
            active_superusers_count = User.objects.filter(is_superuser=True, is_active=True, is_deleted=False).count()
            if active_superusers_count <= 1:
                raise ValidationError("Cannot deactivate the final Super Admin.")

        # Validation: Cannot deactivate the final administrator (ADMIN role)
        if user.has_role('ADMIN'):
            active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
            if active_admins_count <= 1:
                raise ValidationError("Cannot deactivate the final administrator.")

        user.is_active = False
        if admin_user:
            user.updated_by = admin_user
        user.save()

        # Deactivate all active sessions for security
        SessionService.deactivate_all_sessions(user)

        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            target_user=user,
            action=ActivityType.USER_DISABLED,
            description=f"Admin {admin_email} deactivated user {user.email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def reset_password_by_admin(user, new_password, admin_user=None, ip_address=None) -> None:
        """
        Resets a user's password by an admin.
        """
        user.set_password(new_password)
        if admin_user:
            user.updated_by = admin_user
        user.save()

        # Deactivate all active sessions for security
        SessionService.deactivate_all_sessions(user)

        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            target_user=user,
            action=ActivityType.PASSWORD_RESET,
            description=f"Admin {admin_email} reset password for user {user.email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def assign_roles(user, role_names, admin_user=None, ip_address=None) -> list:
        """
        Assigns multiple roles to a user.
        """
        if not isinstance(role_names, list) or not role_names:
            raise ValidationError("role_names must be a non-empty list.")

        normalized_names = [r.upper() for r in role_names]
        if len(normalized_names) != len(set(normalized_names)):
            raise ValidationError("Duplicate roles are not allowed.")

        for name in normalized_names:
            if not Role.objects.filter(name=name).exists():
                raise ValidationError(f"Invalid role: {name}")

        assigned = []
        for name in normalized_names:
            role = Role.objects.get(name=name)
            user_role, created = UserRole.objects.get_or_create(user=user, role=role)
            if created:
                assigned.append(name)
                ActivityLog.objects.create(
                    user=admin_user,
                    target_user=user,
                    action=ActivityType.ROLE_ASSIGNED,
                    description=f"Admin {admin_user.email if admin_user else 'System'} assigned role {name} to user {user.email}.",
                    ip_address=ip_address
                )

        if assigned and admin_user:
            user.updated_by = admin_user
            user.save()

        return assigned

    @staticmethod
    @transaction.atomic
    def remove_roles(user, role_names, admin_user=None, ip_address=None) -> list:
        """
        Removes multiple roles from a user.
        """
        if not isinstance(role_names, list) or not role_names:
            raise ValidationError("role_names must be a non-empty list.")

        normalized_names = [r.upper() for r in role_names]

        for name in normalized_names:
            if not Role.objects.filter(name=name).exists():
                raise ValidationError(f"Invalid role: {name}")
            if not user.roles.filter(name=name).exists():
                raise ValidationError(f"Role {name} is not assigned to the user.")

        # Validation: Cannot remove the last ADMIN role from the final administrator
        if 'ADMIN' in normalized_names and user.has_role('ADMIN'):
            active_admins_count = User.objects.filter(roles__name='ADMIN', is_active=True, is_deleted=False).count()
            if active_admins_count <= 1:
                raise ValidationError("Cannot remove the last ADMIN role from the final administrator.")

        removed = []
        for name in normalized_names:
            role = Role.objects.get(name=name)
            deleted_count, _ = UserRole.objects.filter(user=user, role=role).delete()
            if deleted_count > 0:
                removed.append(name)
                ActivityLog.objects.create(
                    user=admin_user,
                    target_user=user,
                    action=ActivityType.ROLE_REMOVED,
                    description=f"Admin {admin_user.email if admin_user else 'System'} removed role {name} from user {user.email}.",
                    ip_address=ip_address
                )

        if removed and admin_user:
            user.updated_by = admin_user
            user.save()

        return removed
