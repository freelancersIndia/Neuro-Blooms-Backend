import logging
import datetime
from django.db import models, transaction
from django.utils import timezone
from django.db.models import Q, Max
from rest_framework.exceptions import ValidationError, NotFound

from apps.consultations.models import AppointmentRequest, Patient
from apps.consultations.choices import AppointmentRequestStatus, PatientStatus
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

logger = logging.getLogger(__name__)

class PatientMatchingService:

    @staticmethod
    def calculate_matching_score(appt_request: AppointmentRequest, patient: Patient) -> float:
        """
        Calculates the weighted matching score between an appointment request and an existing patient.
        
        Weights:
        - Mobile Number: 50%
        - Child Full Name (First: 10%, Last: 10%): 20%
        - Date of Birth: 20%
        - Parent Name (First: 5%, Last: 5%): 10%
        Total: 100%
        """
        score = 0.0

        # 1. Mobile Number (50%)
        req_mobile = (appt_request.mobile_number or '').strip().replace(' ', '').replace('-', '')
        pat_mobile = (patient.mobile_number or '').strip().replace(' ', '').replace('-', '')
        pat_alt_mobile = (patient.alternate_mobile_number or '').strip().replace(' ', '').replace('-', '')
        
        if req_mobile and (req_mobile == pat_mobile or (pat_alt_mobile and req_mobile == pat_alt_mobile)):
            score += 50.0

        # 2. Child Full Name (20%)
        req_child_first = (appt_request.child_first_name or '').strip().lower()
        pat_child_first = (patient.child_first_name or '').strip().lower()
        req_child_last = (appt_request.child_last_name or '').strip().lower()
        pat_child_last = (patient.child_last_name or '').strip().lower()

        if req_child_first and req_child_first == pat_child_first:
            score += 10.0
        if req_child_last and req_child_last == pat_child_last:
            score += 10.0

        # 3. Date of Birth (20%)
        if appt_request.date_of_birth and appt_request.date_of_birth == patient.date_of_birth:
            score += 20.0

        # 4. Parent Name (10%)
        req_parent_first = (appt_request.parent_first_name or '').strip().lower()
        pat_parent_first = (patient.parent_first_name or '').strip().lower()
        req_parent_last = (appt_request.parent_last_name or '').strip().lower()
        pat_parent_last = (patient.parent_last_name or '').strip().lower()

        if req_parent_first and req_parent_first == pat_parent_first:
            score += 5.0
        if req_parent_last and req_parent_last == pat_parent_last:
            score += 5.0

        return score

    @staticmethod
    def get_confidence_level(score: float) -> str:
        """
        Returns confidence level string based on matching score.
        """
        if score >= 90.0:
            return "Very High Match"
        elif score >= 75.0:
            return "High Match"
        elif score >= 60.0:
            return "Possible Match"
        else:
            return "Low Confidence"

    @classmethod
    def get_duplicate_candidates(cls, appt_request: AppointmentRequest) -> list:
        """
        Searches the Patient table for potential duplicates based on indexed fields,
        calculates matching scores, sorts descending, and returns candidate objects.
        """
        # Filter patients that match at least one attribute to avoid full table scans
        candidates = Patient.objects.filter(
            Q(mobile_number=appt_request.mobile_number) |
            Q(alternate_mobile_number=appt_request.mobile_number) |
            Q(child_first_name__iexact=appt_request.child_first_name) |
            Q(child_last_name__iexact=appt_request.child_last_name) |
            Q(date_of_birth=appt_request.date_of_birth) |
            Q(parent_first_name__iexact=appt_request.parent_first_name) |
            Q(parent_last_name__iexact=appt_request.parent_last_name)
        ).only(
            'id', 'patient_number', 'parent_first_name', 'parent_last_name',
            'relationship_to_child', 'mobile_number', 'alternate_mobile_number',
            'email', 'child_first_name', 'child_last_name', 'date_of_birth',
            'gender', 'patient_status'
        )

        results = []
        for patient in candidates:
            score = cls.calculate_matching_score(appt_request, patient)
            confidence = cls.get_confidence_level(score)
            results.append({
                "patient": patient,
                "score": score,
                "confidence_level": confidence
            })

        # Sort highest score first
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    @staticmethod
    def generate_patient_number() -> str:
        """
        Generates a unique patient number sequentially in the format NBP-XXXXXX.
        Must be called within an active transaction block.
        """
        prefix = "NBP-"
        last_patient = Patient.objects.select_for_update().filter(
            patient_number__startswith=prefix
        ).order_by('-patient_number').first()

        if last_patient:
            try:
                numeric_part = last_patient.patient_number.replace(prefix, "")
                last_seq = int(numeric_part)
                new_seq = last_seq + 1
            except (ValueError, IndexError):
                new_seq = 1
        else:
            new_seq = 1

        return f"{prefix}{new_seq:06d}"

    @classmethod
    def get_patient_matching_screen_data(cls, appointment_request_id: str, user, ip_address: str = None) -> dict:
        """
        Performs validation checks and loads the screen data for the Patient Matching module.
        """
        try:
            appt_request = AppointmentRequest.objects.get(id=appointment_request_id)
        except (AppointmentRequest.DoesNotExist, ValidationError):
            raise NotFound("Appointment request not found.")

        # Business Rule Validations
        if appt_request.status == AppointmentRequestStatus.PATIENT_LINKED:
            raise ValidationError("Appointment request has already been linked to a patient.")
        if appt_request.status == AppointmentRequestStatus.PATIENT_CREATED:
            raise ValidationError("A patient record has already been created for this appointment request.")
        if appt_request.status != AppointmentRequestStatus.APPROVED:
            raise ValidationError("Only approved appointment requests can enter the patient matching workflow.")

        # Create Activity Log for starting matching
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.PATIENT_MATCHING_STARTED,
            description=f"Patient matching process started. Request Number: {appt_request.request_number}",
            ip_address=ip_address
        )

        candidates = cls.get_duplicate_candidates(appt_request)
        
        # Calculate best match score
        best_match_score = candidates[0]["score"] if candidates else 0.0

        return {
            "appointment_request": appt_request,
            "best_match_score": best_match_score,
            "matching_patients": candidates,
            "matching_statistics": {
                "total_candidates": len(candidates),
                "very_high_matches": sum(1 for c in candidates if c["score"] >= 90.0),
                "high_matches": sum(1 for c in candidates if 75.0 <= c["score"] < 90.0),
                "possible_matches": sum(1 for c in candidates if 60.0 <= c["score"] < 75.0),
                "low_confidence_matches": sum(1 for c in candidates if c["score"] < 60.0),
            }
        }

    @classmethod
    def link_patient(cls, appointment_request_id: str, patient_number: str, user, ip_address: str = None) -> dict:
        """
        Links an approved appointment request to an existing active patient.
        All changes run within an atomic transaction.
        """
        try:
            appt_request = AppointmentRequest.objects.get(id=appointment_request_id)
        except (AppointmentRequest.DoesNotExist, ValidationError):
            raise NotFound("Appointment request not found.")

        # Validate appointment request state
        if appt_request.status == AppointmentRequestStatus.PATIENT_LINKED:
            raise ValidationError("Appointment request has already been linked to a patient.")
        if appt_request.status == AppointmentRequestStatus.PATIENT_CREATED:
            raise ValidationError("A patient record has already been created for this appointment request.")
        if appt_request.status != AppointmentRequestStatus.APPROVED:
            raise ValidationError("Only approved appointment requests can be linked to a patient.")

        # Validate patient
        try:
            patient = Patient.objects.get(patient_number=patient_number)
        except Patient.DoesNotExist:
            raise ValidationError("Patient with the provided ID does not exist.")

        if patient.patient_status == PatientStatus.INACTIVE or not patient.is_active:
            raise ValidationError("Cannot link to an inactive patient.")

        with transaction.atomic():
            # Update AppointmentRequest fields
            appt_request.patient = patient
            appt_request.status = AppointmentRequestStatus.PATIENT_LINKED
            appt_request.patient_linked_by = user
            appt_request.patient_linked_at = timezone.now()
            appt_request.save()

            # Create Activity Log
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.PATIENT_LINKED,
                description=f"Patient linked to request. Request Number: {appt_request.request_number}. Patient ID: {patient.patient_number}",
                ip_address=ip_address
            )

        return {
            "success": True,
            "message": "Patient linked successfully."
        }

    @classmethod
    def create_patient_from_request(cls, appointment_request_id: str, user, ip_address: str = None) -> dict:
        """
        Creates a new Patient from the details of an approved appointment request.
        All changes run within an atomic transaction.
        """
        try:
            appt_request = AppointmentRequest.objects.get(id=appointment_request_id)
        except (AppointmentRequest.DoesNotExist, ValidationError):
            raise NotFound("Appointment request not found.")

        # Validate appointment request state
        if appt_request.status == AppointmentRequestStatus.PATIENT_LINKED:
            raise ValidationError("Appointment request has already been linked to a patient.")
        if appt_request.status == AppointmentRequestStatus.PATIENT_CREATED:
            raise ValidationError("A patient record has already been created for this appointment request.")
        if appt_request.status != AppointmentRequestStatus.APPROVED:
            raise ValidationError("Only approved appointment requests can be converted to new patient records.")

        with transaction.atomic():
            # Generate sequential patient number
            patient_num = cls.generate_patient_number()

            # Create the Patient
            patient = Patient.objects.create(
                patient_number=patient_num,
                parent_first_name=appt_request.parent_first_name,
                parent_last_name=appt_request.parent_last_name,
                relationship_to_child=appt_request.relationship_to_child,
                mobile_number=appt_request.mobile_number,
                alternate_mobile_number=appt_request.alternate_mobile_number,
                email=appt_request.email,
                child_first_name=appt_request.child_first_name,
                child_last_name=appt_request.child_last_name,
                date_of_birth=appt_request.date_of_birth,
                gender=appt_request.gender,
                address="Not Provided",  # fallback address since AppointmentRequest does not collect address
                patient_status=PatientStatus.ACTIVE
            )

            # Update AppointmentRequest fields
            appt_request.patient = patient
            appt_request.status = AppointmentRequestStatus.PATIENT_CREATED
            appt_request.patient_created_by = user
            appt_request.patient_created_at = timezone.now()
            appt_request.save()

            # Create Activity Log
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.PATIENT_CREATED,
                description=f"New patient created and linked to request. Request Number: {appt_request.request_number}. Patient ID: {patient.patient_number}",
                ip_address=ip_address
            )

        return {
            "success": True,
            "message": "Patient created successfully.",
            "data": {
                "patient_id": patient.patient_number
            }
        }
