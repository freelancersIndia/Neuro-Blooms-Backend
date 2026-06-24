import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)

class EmailService:
    @staticmethod
    def _send_email_safe(subject: str, message: str, recipient_list: list, html_message: str = None) -> None:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
        except Exception as e:
            logger.error(
                f"Failed to send email to {recipient_list}. "
                f"Subject: {subject}. Error: {str(e)}",
                exc_info=True
            )

    @staticmethod
    def send_login_otp(email: str, otp_code: str) -> None:
        context = {'otp_code': otp_code}
        html_message = render_to_string('emails/login_otp.html', context)
        EmailService._send_email_safe(
            subject='Your Neuro Blooms Login OTP',
            message=f'Your login OTP is {otp_code}. It is valid for 15 minutes.',
            recipient_list=[email],
            html_message=html_message,
        )

    @staticmethod
    def send_password_reset_otp(email: str, otp_code: str) -> None:
        context = {'otp_code': otp_code}
        html_message = render_to_string('emails/password_reset_otp.html', context)
        EmailService._send_email_safe(
            subject='Your Neuro Blooms Password Reset OTP',
            message=f'Your password reset OTP is {otp_code}. It is valid for 15 minutes.',
            recipient_list=[email],
            html_message=html_message,
        )

    @staticmethod
    def send_account_created(email: str, first_name: str, temporary_password: str = None) -> None:
        context = {
            'first_name': first_name,
            'email': email,
            'temporary_password': temporary_password
        }
        html_message = render_to_string('emails/account_created.html', context)
        EmailService._send_email_safe(
            subject='Welcome to Neuro Blooms!',
            message=f'Welcome {first_name}! Your account has been created.',
            recipient_list=[email],
            html_message=html_message,
        )

    @staticmethod
    def send_password_changed(email: str, first_name: str) -> None:
        context = {'first_name': first_name}
        html_message = render_to_string('emails/password_changed.html', context)
        EmailService._send_email_safe(
            subject='Neuro Blooms - Password Changed Successfully',
            message=f'Hello {first_name}, your password has been changed successfully.',
            recipient_list=[email],
            html_message=html_message,
        )

    @staticmethod
    def send_email_verification_otp(email: str, otp_code: str) -> None:
        context = {'otp_code': otp_code}
        html_message = render_to_string('emails/email_verification.html', context)
        EmailService._send_email_safe(
            subject='Verify Your Neuro Blooms Email',
            message=f'Your email verification OTP is {otp_code}. It is valid for 15 minutes.',
            recipient_list=[email],
            html_message=html_message,
        )

