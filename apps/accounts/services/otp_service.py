import logging
from django.utils import timezone
from datetime import timedelta
from django.core.signing import TimestampSigner
from apps.accounts.models.otp import OTP
from apps.accounts.models.user import User
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.utils.otp import generate_numeric_otp
from apps.accounts.services.email_service import EmailService
from apps.accounts.constants.otp_types import OTPPurpose
from apps.accounts.constants.activity_types import ActivityType

logger = logging.getLogger(__name__)

signer = TimestampSigner()

class OTPService:
    @staticmethod
    def generate_otp(user: User, purpose: str, ip_address: str = None) -> OTP:
        # Mark previous unused OTPs as used/expired
        OTP.objects.filter(user=user, purpose=purpose, is_used=False).update(is_used=True)

        otp_code = generate_numeric_otp(6)
        expires_at = timezone.now() + timedelta(minutes=15)

        otp = OTP.objects.create(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=expires_at,
            is_used=False
        )

        # Trigger emails
        if purpose == OTPPurpose.LOGIN_VERIFICATION:
            EmailService.send_login_otp(user.email, otp_code)
        elif purpose == OTPPurpose.PASSWORD_RESET:
            EmailService.send_password_reset_otp(user.email, otp_code)
        elif purpose == OTPPurpose.EMAIL_VERIFICATION:
            EmailService.send_email_verification_otp(user.email, otp_code)

        return otp

    @staticmethod
    def verify_otp(email: str, otp_code: str, purpose: str, ip_address: str = None) -> str:
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValueError("Invalid email or OTP code.")

        now = timezone.now()
        otp = OTP.objects.filter(
            user=user,
            otp_code=otp_code,
            purpose=purpose,
            is_used=False,
            expires_at__gt=now
        ).first()

        if not otp:
            raise ValueError("Invalid or expired OTP code.")

        otp.is_used = True
        otp.save()

        # Log OTP verification activity
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.OTP_VERIFIED,
            description=f"OTP verified successfully for purpose: {purpose}",
            ip_address=ip_address
        )

        # Generate a signed token to verify authorization for action (like resetting password)
        token = signer.sign(f"{user.email}:{purpose}")
        return token

    @staticmethod
    def verify_signed_token(token: str, purpose: str) -> str:
        if not token:
            raise ValueError("Verification token is required.")

        # Clean the token defensively (strip whitespaces and any surrounding quotes)
        cleaned_token = token.strip().strip('"').strip("'")

        # Check if the user accidentally passed the 6-digit OTP code instead of the signed token
        if cleaned_token.isdigit() and len(cleaned_token) == 6:
            raise ValueError(
                "Invalid token. It looks like you passed the 6-digit OTP code. "
                "Please verify the OTP code first using the '/api/v1/auth/verify-otp/' endpoint "
                "to retrieve the signed password reset token."
            )

        try:
            value = signer.unsign(cleaned_token, max_age=900)  # Valid for 15 minutes
            email, token_purpose = value.split(":")
            if token_purpose != purpose:
                raise ValueError("Invalid token purpose.")
            return email
        except Exception as e:
            logger.error(f"Token verification failed for purpose '{purpose}'. Error: {str(e)}", exc_info=True)
            raise ValueError("Invalid or expired verification token.")
