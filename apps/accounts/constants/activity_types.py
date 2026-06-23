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
    ROLE_ASSIGNED = 'ROLE_ASSIGNED'
    ROLE_REMOVED = 'ROLE_REMOVED'
    USER_DISABLED = 'USER_DISABLED'

    # Security Events
    ACCOUNT_LOCKED = 'ACCOUNT_LOCKED'
    SESSION_REVOKED = 'SESSION_REVOKED'

    CHOICES = [
        (LOGIN, 'Login'),
        (LOGOUT, 'Logout'),
        (FAILED_LOGIN, 'Failed Login'),
        (PASSWORD_RESET, 'Password Reset'),
        (PASSWORD_CHANGED, 'Password Changed'),
        (OTP_VERIFIED, 'OTP Verified'),
        (USER_CREATED, 'User Created'),
        (USER_UPDATED, 'User Updated'),
        (ROLE_ASSIGNED, 'Role Assigned'),
        (ROLE_REMOVED, 'Role Removed'),
        (USER_DISABLED, 'User Disabled'),
        (ACCOUNT_LOCKED, 'Account Locked'),
        (SESSION_REVOKED, 'Session Revoked'),
    ]
