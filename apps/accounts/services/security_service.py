from django.utils import timezone
from datetime import timedelta
from apps.accounts.models.user import User, FailedLoginAttempt, AccountLock
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

class SecurityService:
    @staticmethod
    def is_account_locked(user: User) -> bool:
        now = timezone.now()
        active_lock = AccountLock.objects.filter(
            user=user,
            is_active=True,
            unlock_at__gt=now
        ).first()

        if active_lock:
            return True

        # Deactivate expired locks
        AccountLock.objects.filter(
            user=user,
            is_active=True,
            unlock_at__lte=now
        ).update(is_active=False)

        return False

    @staticmethod
    def record_failed_attempt(email: str, ip_address: str, reason: str) -> None:
        FailedLoginAttempt.objects.create(
            email=email,
            ip_address=ip_address,
            reason=reason
        )

        # Count failures in the last 15 minutes
        time_threshold = timezone.now() - timedelta(minutes=15)
        failed_count = FailedLoginAttempt.objects.filter(
            email=email,
            attempt_time__gte=time_threshold
        ).count()

        if failed_count >= 5:
            try:
                user = User.objects.get(email=email)
                if not SecurityService.is_account_locked(user):
                    unlock_time = timezone.now() + timedelta(minutes=15)
                    AccountLock.objects.create(
                        user=user,
                        unlock_at=unlock_time,
                        reason="TOO_MANY_FAILED_ATTEMPTS",
                        is_active=True
                    )
                    # Log security lock event
                    ActivityLog.objects.create(
                        user=user,
                        action=ActivityType.ACCOUNT_LOCKED,
                        description=f"Account locked due to 5+ failed login attempts. Locked until {unlock_time}.",
                        ip_address=ip_address
                    )
            except User.DoesNotExist:
                pass
