import logging
import datetime
from django.db import models, transaction
from django.utils import timezone
from django.db.models import Q, Max, Min, Count, Avg, Value
from django.db.models.functions import Concat, ExtractYear
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError, NotFound

from apps.consultations.models import Patient, Appointment
from apps.consultations.choices import PatientStatus, Gender
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.services.patient_matching_service import PatientMatchingService

User = get_user_model()
logger = logging.getLogger(__name__)

class PatientService:

    @staticmethod
    def get_patient_statistics() -> dict:
        """
        Calculates aggregate statistics for patients in minimal database hits.
        """
        today = datetime.date.today()
        start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Single aggregate query for patient metrics
        stats = Patient.objects.filter(is_deleted=False).aggregate(
            total_patients=Count('id'),
            active_patients=Count('id', filter=Q(patient_status=PatientStatus.ACTIVE)),
            under_treatment=Count('id', filter=Q(patient_status=PatientStatus.UNDER_TREATMENT)),
            treatment_completed=Count('id', filter=Q(patient_status=PatientStatus.DISCHARGED)),
            inactive_patients=Count('id', filter=Q(patient_status=PatientStatus.INACTIVE)),
            new_this_month=Count('id', filter=Q(created_at__gte=start_of_month)),
            male=Count('id', filter=Q(gender=Gender.MALE)),
            female=Count('id', filter=Q(gender=Gender.FEMALE)),
            average_age=Avg(today.year - ExtractYear('date_of_birth'))
        )

        upcoming_appointments = Appointment.objects.filter(
            appointment_date__gte=today,
            status='CONFIRMED',
            patient__is_deleted=False
        ).count()

        return {
            "total_patients": stats["total_patients"] or 0,
            "active_patients": stats["active_patients"] or 0,
            "under_treatment": stats["under_treatment"] or 0,
            "treatment_completed": stats["treatment_completed"] or 0,
            "inactive_patients": stats["inactive_patients"] or 0,
            "new_this_month": stats["new_this_month"] or 0,
            "male": stats["male"] or 0,
            "female": stats["female"] or 0,
            "average_age": round(stats["average_age"] or 0.0, 1),
            "upcoming_appointments": upcoming_appointments
        }

    @staticmethod
    def get_dob_range_for_age_group(group: str):
        """
        Returns (dob_start, dob_end) range for a given age group filter.
        """
        today = datetime.date.today()
        if group == '0-3':
            return today - datetime.timedelta(days=3*365.25), today
        elif group == '4-6':
            return today - datetime.timedelta(days=6*365.25), today - datetime.timedelta(days=4*365.25)
        elif group == '7-12':
            return today - datetime.timedelta(days=12*365.25), today - datetime.timedelta(days=7*365.25)
        elif group == '13-18':
            return today - datetime.timedelta(days=18*365.25), today - datetime.timedelta(days=13*365.25)
        elif group == '18+':
            return None, today - datetime.timedelta(days=18*365.25)
        return None, None

    @classmethod
    def list_patients(cls, query_params: dict) -> models.QuerySet:
        """
        Retrieves a filtered, searched, and sorted QuerySet of patients with optimized relations and annotations.
        """
        today = datetime.date.today()
        queryset = Patient.objects.filter(is_deleted=False)

        # Annotations to prevent N+1 queries when rendering calculated list fields
        queryset = queryset.annotate(
            patient_name=Concat('child_first_name', Value(' '), 'child_last_name'),
            parent_name=Concat('parent_first_name', Value(' '), 'parent_last_name'),
            last_visit=Max('appointments__appointment_date', filter=Q(appointments__status='COMPLETED')),
            next_appointment=Min('appointments__appointment_date', filter=Q(appointments__appointment_date__gte=today, appointments__status='CONFIRMED'))
        ).select_related('assigned_doctor', 'created_by')

        # 1. Global Search (Case-insensitive, partial matching)
        search = query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(
                Q(patient_number__icontains=search) |
                Q(patient_name__icontains=search) |
                Q(parent_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(alternate_mobile_number__icontains=search) |
                Q(email__icontains=search)
            )

        # 2. Filters
        status_param = query_params.get('status')
        if status_param:
            queryset = queryset.filter(patient_status=status_param)

        gender_param = query_params.get('gender')
        if gender_param:
            queryset = queryset.filter(gender=gender_param)

        doctor_param = query_params.get('doctor')
        if doctor_param:
            queryset = queryset.filter(assigned_doctor_id=doctor_param)

        # Age Group Filter
        age_group = query_params.get('age_group')
        if age_group:
            dob_start, dob_end = cls.get_dob_range_for_age_group(age_group)
            if dob_start:
                queryset = queryset.filter(date_of_birth__gte=dob_start)
            if dob_end:
                queryset = queryset.filter(date_of_birth__lte=dob_end)

        # Registration Date Filter
        reg_start = query_params.get('registration_date_start')
        if reg_start:
            queryset = queryset.filter(created_at__date__gte=reg_start)
        reg_end = query_params.get('registration_date_end')
        if reg_end:
            queryset = queryset.filter(created_at__date__lte=reg_end)

        # Has Upcoming Appointment Filter
        has_upcoming = query_params.get('has_upcoming_appointment')
        if has_upcoming is not None:
            is_true = str(has_upcoming).lower() in ['true', '1', 'yes']
            if is_true:
                queryset = queryset.filter(appointments__appointment_date__gte=today, appointments__status='CONFIRMED').distinct()
            else:
                queryset = queryset.exclude(appointments__appointment_date__gte=today, appointments__status='CONFIRMED')

        # 3. Ordering Mapping
        ordering_param = query_params.get('ordering', '-created_at')
        ordering_map = {
            'created_at': ['created_at'],
            '-created_at': ['-created_at'],
            'child_name': ['child_first_name', 'child_last_name'],
            '-child_name': ['-child_first_name', '-child_last_name'],
            'last_visit': ['last_visit'],
            '-last_visit': ['-last_visit'],
            'next_appointment': ['next_appointment'],
            '-next_appointment': ['-next_appointment']
        }
        order_fields = ordering_map.get(ordering_param, ['-created_at'])
        
        # Ensure tie-breaker order key
        if 'id' not in order_fields and '-id' not in order_fields:
            order_fields.append('-id')

        return queryset.order_by(*order_fields)

    @classmethod
    def create_patient(cls, validated_data: dict, user, ip_address: str = None) -> Patient:
        """
        Registers a new patient manually, performing validation and logging.
        """
        child_first_name = validated_data.get('child_first_name')
        child_last_name = validated_data.get('child_last_name')
        mobile_number = validated_data.get('mobile_number')
        date_of_birth = validated_data.get('date_of_birth')

        # 1. Validation: Future DOB Check
        if date_of_birth and date_of_birth > datetime.date.today():
            raise ValidationError({"date_of_birth": ["Date of birth cannot be a future date."]})

        # 2. Validation: Unique Mobile + Child check
        duplicate_exists = Patient.objects.filter(
            mobile_number=mobile_number,
            child_first_name__iexact=child_first_name,
            child_last_name__iexact=child_last_name,
            is_deleted=False
        ).exists()
        
        if duplicate_exists:
            raise ValidationError("A patient record with the same child name and mobile number already exists.")

        with transaction.atomic():
            # 3. Generate sequential patient ID
            patient_num = PatientMatchingService.generate_patient_number()

            # 4. Create record
            patient = Patient.objects.create(
                patient_number=patient_num,
                created_by=user,
                **validated_data
            )

            # 5. Log Activity
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.PATIENT_CREATED,
                description=f"Patient registered manually. Patient ID: {patient.patient_number}",
                ip_address=ip_address
            )

        return patient

    @classmethod
    def update_patient(cls, patient: Patient, validated_data: dict, user, ip_address: str = None) -> Patient:
        """
        Updates patient details, preventing edits to read-only fields.
        """
        # Block attempts to update read-only fields
        read_only_fields = ['patient_number', 'patient_id', 'created_at', 'created_by']
        for field in read_only_fields:
            if field in validated_data:
                validated_data.pop(field)

        status_changed = False
        old_status = patient.patient_status
        new_status = validated_data.get('patient_status')
        if new_status and old_status != new_status:
            status_changed = True

        doctor_changed = False
        old_doctor = patient.assigned_doctor
        new_doctor = validated_data.get('assigned_doctor')
        if 'assigned_doctor' in validated_data and old_doctor != new_doctor:
            doctor_changed = True

        # Perform update
        for field, value in validated_data.items():
            setattr(patient, field, value)
        patient.save()

        # Log Activity Logs
        description_parts = [f"Patient profile updated. Patient ID: {patient.patient_number}."]
        if status_changed:
            ActivityLog.objects.create(
                user=user,
                action='PATIENT_STATUS_CHANGED',
                description=f"Patient status changed from '{old_status}' to '{new_status}'. Patient ID: {patient.patient_number}",
                ip_address=ip_address
            )
        if doctor_changed:
            doc_email = new_doctor.email if new_doctor else "None"
            ActivityLog.objects.create(
                user=user,
                action='PATIENT_ASSIGNED_DOCTOR',
                description=f"Assigned doctor updated to '{doc_email}'. Patient ID: {patient.patient_number}",
                ip_address=ip_address
            )

        ActivityLog.objects.create(
            user=user,
            action=ActivityType.PATIENT_UPDATED,
            description=" ".join(description_parts),
            ip_address=ip_address
        )

        return patient

    @classmethod
    def soft_delete_patient(cls, patient: Patient, user, ip_address: str = None):
        """
        Soft deletes a patient record.
        """
        with transaction.atomic():
            patient.is_deleted = True
            patient.deleted_at = timezone.now()
            patient.deleted_by = user
            patient.save()

            # Create Activity Log
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.PATIENT_DELETED,
                description=f"Patient soft deleted. Patient ID: {patient.patient_number}",
                ip_address=ip_address
            )

    @staticmethod
    def get_filter_options() -> dict:
        """
        Fetches metadata choices and reference data for filter dropdowns.
        """
        # Fetch distinct active doctors
        doctors_qs = User.objects.filter(
            user_roles__role__name='DOCTOR',
            is_active=True
        ).distinct().order_by('first_name', 'last_name')
        
        doctors_list = [
            {
                "id": doc.id,
                "name": f"Dr. {doc.first_name} {doc.last_name}",
                "email": doc.email
            } for doc in doctors_qs
        ]

        # Standard static metadata options
        age_groups = [
            {"key": "0-3", "label": "0-3 Years (Toddler)"},
            {"key": "4-6", "label": "4-6 Years (Preschooler)"},
            {"key": "7-12", "label": "7-12 Years (School Age)"},
            {"key": "13-18", "label": "13-18 Years (Adolescent)"},
            {"key": "18+", "label": "18+ Years (Adult)"}
        ]

        languages = ["English", "Hindi", "Kannada", "Tamil", "Telugu", "Malayalam"]

        referral_sources = ["Google Search", "Doctor Referral", "Word of Mouth", "Social Media", "Website", "Other"]

        return {
            "statuses": [
                {"key": choice[0], "label": choice[1]} for choice in PatientStatus.choices
            ],
            "genders": [
                {"key": choice[0], "label": choice[1]} for choice in Gender.choices
            ],
            "doctors": doctors_list,
            "age_groups": age_groups,
            "languages": languages,
            "referral_sources": referral_sources
        }

    @classmethod
    def perform_bulk_action(cls, patient_ids: list, action: str, extra_data: dict, user, ip_address: str = None) -> dict:
        """
        Atomically applies bulk operation (assign doctor, archive, status state toggles) to list of patients.
        """
        if not patient_ids:
            raise ValidationError("Patient ID list cannot be empty.")

        with transaction.atomic():
            patients = Patient.objects.filter(id__in=patient_ids)
            count = patients.count()

            if action == "assign_doctor":
                doctor_id = extra_data.get("doctor_id")
                if not doctor_id:
                    raise ValidationError("Doctor ID is required for assignment.")
                try:
                    doctor = User.objects.get(id=doctor_id, user_roles__role__name='DOCTOR')
                except User.DoesNotExist:
                    raise ValidationError("Valid active doctor not found.")

                patients.update(assigned_doctor=doctor)

                for p in patients:
                    ActivityLog.objects.create(
                        user=user,
                        action='PATIENT_ASSIGNED_DOCTOR',
                        description=f"Bulk doctor assignment: Dr. {doctor.email}. Patient ID: {p.patient_number}",
                        ip_address=ip_address
                    )

                message = f"Successfully assigned Dr. {doctor.first_name} {doctor.last_name} to {count} patients."

            elif action == "archive":
                # Ensure only ADMIN can soft delete/archive
                if not user.has_role('ADMIN'):
                    raise ValidationError("Only administrators are permitted to archive patient profiles.")

                patients.update(is_deleted=True, deleted_at=timezone.now(), deleted_by=user)

                for p in patients:
                    ActivityLog.objects.create(
                        user=user,
                        action=ActivityType.PATIENT_DELETED,
                        description=f"Bulk archive/soft-delete. Patient ID: {p.patient_number}",
                        ip_address=ip_address
                    )

                message = f"Successfully archived {count} patients."

            elif action in ["activate", "deactivate"]:
                new_status = PatientStatus.ACTIVE if action == "activate" else PatientStatus.INACTIVE
                patients.update(patient_status=new_status)

                for p in patients:
                    ActivityLog.objects.create(
                        user=user,
                        action='PATIENT_STATUS_CHANGED',
                        description=f"Bulk status update: {new_status}. Patient ID: {p.patient_number}",
                        ip_address=ip_address
                    )

                message = f"Successfully updated status to {new_status} for {count} patients."

            else:
                raise ValidationError(f"Invalid bulk action '{action}'.")

            return {
                "success": True,
                "message": message,
                "affected_count": count
            }
