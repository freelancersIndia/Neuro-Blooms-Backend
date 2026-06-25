from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError, NotFound

from apps.accounts.models.user import User, Role, UserRole, AccountLock, FailedLoginAttempt
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.accounts.selectors.user import get_user_by_id

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
        user = get_user_by_id(user_id)
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
                user.is_active = is_active
                updated_fields.append('is_active')

        if is_verified is not None:
            if user.is_verified != is_verified:
                user.is_verified = is_verified
                updated_fields.append('is_verified')

        user.save()

        # Update Roles
        if roles is not None:
            normalized_roles = [r.upper() for r in roles]
            if len(normalized_roles) != len(set(normalized_roles)):
                raise ValidationError({"roles": ["Duplicate roles are not allowed."]})
            
            for role_name in normalized_roles:
                if not Role.objects.filter(name=role_name).exists():
                    raise ValidationError({"roles": [f"Invalid role: {role_name}"]})

            existing_roles = [r.name for r in user.roles.all()]
            if set(existing_roles) != set(normalized_roles):
                UserRole.objects.filter(user=user).delete()
                for role_name in normalized_roles:
                    role = Role.objects.get(name=role_name)
                    UserRole.objects.create(user=user, role=role)
                updated_fields.append('roles')

        # Log administrative action
        if updated_fields:
            admin_email = admin_user.email if admin_user else "System"
            ActivityLog.objects.create(
                user=admin_user,
                action=ActivityType.USER_UPDATED,
                description=f"Admin {admin_email} updated user {user.email}. Updated fields: {', '.join(updated_fields)}.",
                ip_address=ip_address
            )

        return user

    @staticmethod
    @transaction.atomic
    def lock_user(user, admin_user=None, ip_address=None, reason="Manual lock by administrator") -> None:
        """
        Manually locks a user account by creating an AccountLock.
        """
        now = timezone.now()
        active_lock = user.locks.filter(is_active=True, unlock_at__gt=now).first()
        if active_lock:
            raise ValidationError("User account is already locked.")

        # Manual lock lasts 99 years (effectively permanent until unlocked)
        unlock_at = now + timezone.timedelta(days=365 * 99)
        AccountLock.objects.create(
            user=user,
            unlock_at=unlock_at,
            reason=reason,
            is_active=True
        )

        # Log activity
        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
            action=ActivityType.USER_LOCKED,
            description=f"Admin {admin_email} locked user {user.email}.",
            ip_address=ip_address
        )

    @staticmethod
    @transaction.atomic
    def unlock_user(user, admin_user=None, ip_address=None) -> None:
        """
        Manually unlocks a user account, deactivating active locks and resetting failed login attempts.
        """
        now = timezone.now()
        active_locks = user.locks.filter(is_active=True, unlock_at__gt=now)
        if not active_locks.exists():
            raise ValidationError("User account is not locked.")

        active_locks.update(is_active=False)

        # Reset failed attempts
        FailedLoginAttempt.objects.filter(email=user.email).delete()

        # Log activity
        admin_email = admin_user.email if admin_user else "System"
        ActivityLog.objects.create(
            user=admin_user,
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
        Permanently deletes a user account, verifying self-deletion and superuser constraints.
        """
        if user.id == admin_user.id:
            raise ValidationError("Administrators cannot delete their own account.")

        if user.is_superuser:
            raise ValidationError("Superusers cannot be deleted.")

        email = user.email

        # Perform cascading delete
        user.delete()

        # Log activity
        admin_email = admin_user.email
        ActivityLog.objects.create(
            user=admin_user,
            action=ActivityType.USER_DELETED,
            description=f"Admin {admin_email} deleted user {email}.",
            ip_address=ip_address
        )
