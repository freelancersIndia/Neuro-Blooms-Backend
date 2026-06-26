class ActivityType:
    # Authentication Events
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    FAILED_LOGIN = 'FAILED_LOGIN'
    PASSWORD_RESET = 'PASSWORD_RESET'
    PASSWORD_CHANGED = 'PASSWORD_CHANGED'
    OTP_VERIFIED = 'OTP_VERIFIED'

    # Administrative Events
    USER_CREATED = 'USER_CREATED'
    USER_UPDATED = 'USER_UPDATED'
    USER_LOCKED = 'USER_LOCKED'
    USER_UNLOCKED = 'USER_UNLOCKED'
    USER_DELETED = 'USER_DELETED'
    ROLE_ASSIGNED = 'ROLE_ASSIGNED'
    ROLE_REMOVED = 'ROLE_REMOVED'
    USER_DISABLED = 'USER_DISABLED'

    # Security Events
    ACCOUNT_LOCKED = 'ACCOUNT_LOCKED'
    SESSION_REVOKED = 'SESSION_REVOKED'

    # Hardening Events
    ROLE_SEEDED = 'ROLE_SEEDED'
    INITIAL_ADMIN_CREATED = 'INITIAL_ADMIN_CREATED'
    ACCOUNT_UNLOCKED = 'ACCOUNT_UNLOCKED'
    EMAIL_VERIFICATION_SENT = 'EMAIL_VERIFICATION_SENT'
    EMAIL_VERIFIED = 'EMAIL_VERIFIED'
    CONSULTATION_REQUEST_CREATED = 'CONSULTATION_REQUEST_CREATED'
    APPOINTMENT_REQUEST_VIEWED = 'APPOINTMENT_REQUEST_VIEWED'
    APPOINTMENT_REQUEST_APPROVED = 'APPOINTMENT_REQUEST_APPROVED'
    APPOINTMENT_REQUEST_REJECTED = 'APPOINTMENT_REQUEST_REJECTED'

    CHOICES = [
        (LOGIN, 'Login'),
        (LOGOUT, 'Logout'),
        (FAILED_LOGIN, 'Failed Login'),
        (PASSWORD_RESET, 'Password Reset'),
        (PASSWORD_CHANGED, 'Password Changed'),
        (OTP_VERIFIED, 'OTP Verified'),
        (USER_CREATED, 'User Created'),
        (USER_UPDATED, 'User Updated'),
        (USER_LOCKED, 'User Locked'),
        (USER_UNLOCKED, 'User Unlocked'),
        (USER_DELETED, 'User Deleted'),
        (ROLE_ASSIGNED, 'Role Assigned'),
        (ROLE_REMOVED, 'Role Removed'),
        (USER_DISABLED, 'User Disabled'),
        (ACCOUNT_LOCKED, 'Account Locked'),
        (SESSION_REVOKED, 'Session Revoked'),
        (ROLE_SEEDED, 'Role Seeded'),
        (INITIAL_ADMIN_CREATED, 'Initial Admin Created'),
        (ACCOUNT_UNLOCKED, 'Account Unlocked'),
        (EMAIL_VERIFICATION_SENT, 'Email Verification Sent'),
        (EMAIL_VERIFIED, 'Email Verified'),
        (CONSULTATION_REQUEST_CREATED, 'Consultation Request Created'),
        (APPOINTMENT_REQUEST_VIEWED, 'Appointment Request Viewed'),
        (APPOINTMENT_REQUEST_APPROVED, 'Appointment Request Approved'),
        (APPOINTMENT_REQUEST_REJECTED, 'Appointment Request Rejected'),
    ]
