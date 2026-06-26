from django.db import models

class Gender(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER = 'OTHER', 'Other'

class RelationshipToChild(models.TextChoices):
    FATHER = 'FATHER', 'Father'
    MOTHER = 'MOTHER', 'Mother'
    GUARDIAN = 'GUARDIAN', 'Guardian'
    OTHER = 'OTHER', 'Other'

class AppointmentRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'

class BookingSource(models.TextChoices):
    WEBSITE = 'WEBSITE', 'Website'
    ADMIN_PANEL = 'ADMIN_PANEL', 'Admin Panel'
    RECEPTIONIST = 'RECEPTIONIST', 'Receptionist'
    WHATSAPP = 'WHATSAPP', 'WhatsApp'

class PatientStatus(models.TextChoices):
    ACTIVE = 'ACTIVE', 'Active'
    UNDER_TREATMENT = 'UNDER_TREATMENT', 'Under Treatment'
    FOLLOW_UP = 'FOLLOW_UP', 'Follow Up'
    DISCHARGED = 'DISCHARGED', 'Discharged'
    INACTIVE = 'INACTIVE', 'Inactive'

class AppointmentType(models.TextChoices):
    INITIAL = 'INITIAL', 'Initial'
    FOLLOW_UP = 'FOLLOW_UP', 'Follow Up'
    REVIEW = 'REVIEW', 'Review'

class AppointmentStatus(models.TextChoices):
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    IN_CONSULTATION = 'IN_CONSULTATION', 'In Consultation'
    COMPLETED = 'COMPLETED', 'Completed'
    RESCHEDULED = 'RESCHEDULED', 'Rescheduled'
    CANCELLED = 'CANCELLED', 'Cancelled'
    NO_SHOW = 'NO_SHOW', 'No Show'

class SlotStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    BOOKED = 'BOOKED', 'Booked'
    BLOCKED = 'BLOCKED', 'Blocked'

class Weekday(models.IntegerChoices):
    MONDAY = 0, 'Monday'
    TUESDAY = 1, 'Tuesday'
    WEDNESDAY = 2, 'Wednesday'
    THURSDAY = 3, 'Thursday'
    FRIDAY = 4, 'Friday'
    SATURDAY = 5, 'Saturday'
    SUNDAY = 6, 'Sunday'

class NoteVisibility(models.TextChoices):
    PRIVATE = 'PRIVATE', 'Private'
    DOCTOR_ONLY = 'DOCTOR_ONLY', 'Doctor Only'
