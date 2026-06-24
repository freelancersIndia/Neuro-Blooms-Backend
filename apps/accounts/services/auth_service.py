from rest_framework_simplejwt.tokens import RefreshToken
from apps.accounts.models.user import User
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.services.security_service import SecurityService
from apps.accounts.services.session_service import SessionService
from apps.accounts.constants.activity_types import ActivityType

class AuthService:
    @staticmethod
    def validate_credentials_and_send_otp(email: str, password: str, ip_address: str) -> User:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            SecurityService.record_failed_attempt(email, ip_address, "USER_NOT_FOUND")
            raise ValueError("Invalid email or password.")

        if SecurityService.is_account_locked(user):
            SecurityService.record_failed_attempt(email, ip_address, "ACCOUNT_LOCKED")
            raise ValueError("This account is temporarily locked. Please try again in 15 minutes.")

        if not user.check_password(password):
            SecurityService.record_failed_attempt(email, ip_address, "INVALID_PASSWORD")
            raise ValueError("Invalid email or password.")

        if not user.is_active:
            raise ValueError("Account is deactivated.")

        # Generate LOGIN_VERIFICATION OTP
        from apps.accounts.services.otp_service import OTPService
        from apps.accounts.constants.otp_types import OTPPurpose
        OTPService.generate_otp(user, OTPPurpose.LOGIN_VERIFICATION, ip_address)

        return user

    @staticmethod
    def verify_login_otp(email: str, otp_code: str, ip_address: str, user_agent: str) -> dict:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("Invalid email or OTP code.")

        if SecurityService.is_account_locked(user):
            raise ValueError("This account is temporarily locked. Please try again in 15 minutes.")

        if not user.is_active:
            raise ValueError("Account is deactivated.")

        # Verify the OTP code
        from apps.accounts.services.otp_service import OTPService
        from apps.accounts.constants.otp_types import OTPPurpose
        OTPService.verify_otp(email, otp_code, OTPPurpose.LOGIN_VERIFICATION, ip_address)

        # Generate SimpleJWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)
        jti = refresh.payload.get('jti')

        # Create active device session
        SessionService.create_session(
            user=user,
            refresh_token_jti=jti,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Log successful login
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.LOGIN,
            description="User logged in successfully via two-step OTP verification.",
            ip_address=ip_address
        )

        return {
            'access': access_token,
            'refresh': refresh_token,
            'user': user
        }


    @staticmethod
    def logout_user(refresh_token: str, ip_address: str = None) -> None:
        try:
            token = RefreshToken(refresh_token)
            jti = token.payload.get('jti')

            # 1. Blacklist refresh token
            token.blacklist()

            # 2. Deactivate device session
            SessionService.deactivate_session(jti)

            # 3. Log logout event
            user_id = token.payload.get('user_id')
            user = User.objects.filter(id=user_id).first()
            if user:
                ActivityLog.objects.create(
                    user=user,
                    action=ActivityType.LOGOUT,
                    description="User logged out successfully.",
                    ip_address=ip_address
                )
        except Exception:
            raise ValueError("Invalid or expired refresh token.")

    @staticmethod
    def change_password(user: User, current_password: str, new_password: str, ip_address: str = None) -> None:
        if not user.check_password(current_password):
            raise ValueError("Invalid current password.")

        user.set_password(new_password)
        user.save()

        # Log change password event
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.PASSWORD_CHANGED,
            description="Password changed successfully.",
            ip_address=ip_address
        )

        # Notify via email
        from apps.accounts.services.email_service import EmailService
        EmailService.send_password_changed(user.email, user.first_name)

    @staticmethod
    def forgot_password(email: str, ip_address: str = None) -> None:
        try:
            user = User.objects.get(email=email)
            from apps.accounts.services.otp_service import OTPService
            from apps.accounts.constants.otp_types import OTPPurpose
            OTPService.generate_otp(user, OTPPurpose.PASSWORD_RESET, ip_address)
        except User.DoesNotExist:
            # Prevent email harvesting by silently returning success
            pass

    @staticmethod
    def reset_password(token: str, new_password: str, ip_address: str = None) -> None:
        from apps.accounts.services.otp_service import OTPService
        from apps.accounts.constants.otp_types import OTPPurpose

        # Verify signed token
        email = OTPService.verify_signed_token(token, OTPPurpose.PASSWORD_RESET)

        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()

            # Log password reset activity
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.PASSWORD_CHANGED,
                description="Password reset via OTP verified successfully.",
                ip_address=ip_address
            )

            # Send email confirmation
            from apps.accounts.services.email_service import EmailService
            EmailService.send_password_changed(user.email, user.first_name)

            # Terminate other sessions for security
            SessionService.deactivate_all_sessions(user)
        except User.DoesNotExist:
            raise ValueError("User does not exist.")
