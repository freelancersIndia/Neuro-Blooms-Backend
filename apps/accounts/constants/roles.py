class SystemRole:
    ADMIN = 'ADMIN'
    DOCTOR = 'DOCTOR'
    RECEPTIONIST = 'RECEPTIONIST'

    ALL = [ADMIN, DOCTOR, RECEPTIONIST]

    CHOICES = [
        (ADMIN, 'Admin'),
        (DOCTOR, 'Doctor'),
        (RECEPTIONIST, 'Receptionist'),
    ]
