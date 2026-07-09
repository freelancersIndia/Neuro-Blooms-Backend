from django.db import models

class Gender(models.TextChoices):
    MALE = 'MALE', 'Male'
    FEMALE = 'FEMALE', 'Female'
    OTHER = 'OTHER', 'Other'
    PREFER_NOT_TO_SAY = 'PREFER_NOT_TO_SAY', 'Prefer Not To Say'

class RelationshipToChild(models.TextChoices):
    FATHER = 'FATHER', 'Father'
    MOTHER = 'MOTHER', 'Mother'
    GUARDIAN = 'GUARDIAN', 'Guardian'
    GRANDPARENT = 'GRANDPARENT', 'Grandparent'
    OTHER = 'OTHER', 'Other'

class AppointmentRequestStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    PATIENT_LINKED = 'PATIENT_LINKED', 'Patient Linked'
    PATIENT_CREATED = 'PATIENT_CREATED', 'Patient Created'
    RESCHEDULED = 'RESCHEDULED', 'Rescheduled'

class AppointmentRequestTimelineEvent(models.TextChoices):
    SUBMITTED = 'SUBMITTED', 'Request Submitted'
    VIEWED = 'VIEWED', 'Viewed'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    PATIENT_CREATED = 'PATIENT_CREATED', 'Patient Created'
    PATIENT_LINKED = 'PATIENT_LINKED', 'Patient Linked'
    APPOINTMENT_CREATED = 'APPOINTMENT_CREATED', 'Appointment Created'
    SUMMARY_PRINTED = 'SUMMARY_PRINTED', 'Summary Printed'
    EXPORTED = 'EXPORTED', 'Exported'
    NOTES_ADDED = 'NOTES_ADDED', 'Notes Added'


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
    INITIAL_CONSULTATION = 'INITIAL_CONSULTATION', 'Initial Consultation'
    DEVELOPMENT_ASSESSMENT = 'DEVELOPMENT_ASSESSMENT', 'Development Assessment'

class AppointmentStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    CONFIRMED = 'CONFIRMED', 'Confirmed'
    CHECKED_IN = 'CHECKED_IN', 'Checked In'
    IN_CONSULTATION = 'IN_CONSULTATION', 'In Consultation'
    COMPLETED = 'COMPLETED', 'Completed'
    CANCELLED = 'CANCELLED', 'Cancelled'
    NO_SHOW = 'NO_SHOW', 'No Show'
    RESCHEDULED = 'RESCHEDULED', 'Rescheduled'

class SlotStatus(models.TextChoices):
    AVAILABLE = 'AVAILABLE', 'Available'
    BOOKED = 'BOOKED', 'Booked'
    BLOCKED = 'BLOCKED', 'Blocked'

class Weekday(models.TextChoices):
    MONDAY = 'MONDAY', 'Monday'
    TUESDAY = 'TUESDAY', 'Tuesday'
    WEDNESDAY = 'WEDNESDAY', 'Wednesday'
    THURSDAY = 'THURSDAY', 'Thursday'
    FRIDAY = 'FRIDAY', 'Friday'
    SATURDAY = 'SATURDAY', 'Saturday'
    SUNDAY = 'SUNDAY', 'Sunday'

class Priority(models.TextChoices):
    LOW = 'LOW', 'Low'
    MEDIUM = 'MEDIUM', 'Medium'
    HIGH = 'HIGH', 'High'
    URGENT = 'URGENT', 'Urgent'

class ReferralSource(models.TextChoices):
    DIRECT = 'DIRECT', 'Direct'
    DOCTOR_REFERRAL = 'DOCTOR_REFERRAL', 'Doctor Referral'
    SCHOOL_REFERRAL = 'SCHOOL_REFERRAL', 'School Referral'
    WEBSITE = 'WEBSITE', 'Website'
    SOCIAL_MEDIA = 'SOCIAL_MEDIA', 'Social Media'
    OTHER = 'OTHER', 'Other'

class NoteVisibility(models.TextChoices):
    PRIVATE = 'PRIVATE', 'Private'
    DOCTOR_ONLY = 'DOCTOR_ONLY', 'Doctor Only'

class PrimaryConcern(models.TextChoices):
    SPEECH_DELAY = 'SPEECH_DELAY', 'Speech Delay'
    AUTISM_ASSESSMENT = 'AUTISM_ASSESSMENT', 'Autism Assessment'
    BEHAVIOURAL_CONCERNS = 'BEHAVIOURAL_CONCERNS', 'Behavioural Concerns'
    DEVELOPMENTAL_DELAY = 'DEVELOPMENTAL_DELAY', 'Developmental Delay'
    LEARNING_DIFFICULTY = 'LEARNING_DIFFICULTY', 'Learning Difficulty'
    ADHD_ASSESSMENT = 'ADHD_ASSESSMENT', 'ADHD Assessment'
    OCCUPATIONAL_THERAPY = 'OCCUPATIONAL_THERAPY', 'Occupational Therapy'
    PHYSIOTHERAPY = 'PHYSIOTHERAPY', 'Physiotherapy'
    FEEDING_ISSUES = 'FEEDING_ISSUES', 'Feeding Issues'
    OTHER = 'OTHER', 'Other'
