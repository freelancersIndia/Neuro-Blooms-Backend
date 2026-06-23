class OTPPurpose:
    PASSWORD_RESET = 'PASSWORD_RESET'
    LOGIN_VERIFICATION = 'LOGIN_VERIFICATION'
    EMAIL_VERIFICATION = 'EMAIL_VERIFICATION'

    CHOICES = [
        (PASSWORD_RESET, 'Password Reset'),
        (LOGIN_VERIFICATION, 'Login Verification'),
        (EMAIL_VERIFICATION, 'Email Verification'),
    ]
