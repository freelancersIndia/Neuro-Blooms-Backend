import datetime
from django.db import transaction
from django.utils import timezone
from django.db.models import Q
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model

from apps.consultations.models.appointment_request import AppointmentRequest
from apps.consultations.models.patient import Patient
from apps.consultations.models.patient_timeline import PatientTimeline
from apps.consultations.choices import AppointmentRequestStatus
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

User = get_user_model()

class PatientMatchingService:

    @classmethod
    def calculate_match_score(cls, request: AppointmentRequest, patient: Patient) -> dict:
        """
        Calculates the weighted match score between an appointment request and an existing patient.
        """
        score = 0.0
        matched_fields = []

        # 1. Mobile Number (50%)
        req_mob = (request.mobile_number or "").strip()
        pat_mob = (patient.mobile_number or "").strip()
        if req_mob and pat_mob and req_mob == pat_mob:
            score += 50.0
            matched_fields.append("mobile_number")

        # 2. Child Name (20% - 10% first, 10% last)
        req_cfn = (request.child_first_name or "").strip().lower()
        req_cln = (request.child_last_name or "").strip().lower()
        pat_cfn = (patient.child_first_name or "").strip().lower()
        pat_cln = (patient.child_last_name or "").strip().lower()
        child_matched = False

        if req_cfn and pat_cfn and req_cfn == pat_cfn:
            score += 10.0
            child_matched = True
        if req_cln and pat_cln and req_cln == pat_cln:
            score += 10.0
            child_matched = True
        if child_matched:
            matched_fields.append("child_name")

        # 3. Parent Name (15% - 7.5% first, 7.5% last)
        req_pfn = (request.parent_first_name or "").strip().lower()
        req_pln = (request.parent_last_name or "").strip().lower()
        pat_pfn = (patient.parent_first_name or "").strip().lower()
        pat_pln = (patient.parent_last_name or "").strip().lower()
        parent_matched = False

        if req_pfn and pat_pfn and req_pfn == pat_pfn:
            score += 7.5
            parent_matched = True
        if req_pln and pat_pln and req_pln == pat_pln:
            score += 7.5
            parent_matched = True
        if parent_matched:
            matched_fields.append("parent_name")

        # 4. Date of Birth (10%)
        if request.date_of_birth and patient.date_of_birth and request.date_of_birth == patient.date_of_birth:
            score += 10.0
            matched_fields.append("date_of_birth")

        # 5. Gender (5%)
        if request.gender and patient.gender and request.gender == patient.gender:
            score += 5.0
            matched_fields.append("gender")

        # Determine Match Level
        score_round = int(round(score))
        if score_round >= 95:
            match_level = "EXACT_MATCH"
        elif score_round >= 80:
            match_level = "HIGH_PROBABILITY"
        elif score_round >= 60:
            match_level = "POSSIBLE_MATCH"
        else:
            match_level = "NO_MATCH"

        return {
            "score": score_round,
            "match_level": match_level,
            "matched_fields": matched_fields
        }

    @classmethod
    def find_matches(cls, request_id: str) -> dict:
        """
        Retrieves the appointment request and finds potential matching patients in the system.
        """
        request_obj = AppointmentRequest.objects.filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Query potential matches using an OR filter to fetch candidates efficiently
        candidates = Patient.objects.filter(is_deleted=False).filter(
            Q(mobile_number=request_obj.mobile_number) |
            Q(child_first_name__iexact=request_obj.child_first_name) |
            Q(child_last_name__iexact=request_obj.child_last_name) |
            Q(parent_first_name__iexact=request_obj.parent_first_name) |
            Q(parent_last_name__iexact=request_obj.parent_last_name) |
            Q(date_of_birth=request_obj.date_of_birth)
        )

        matches = []
        for candidate in candidates:
            res = cls.calculate_match_score(request_obj, candidate)
            if res["score"] >= 60:
                matches.append({
                    "patient_id": candidate.id,
                    "patient_code": candidate.patient_number,
                    "child_name": f"{candidate.child_first_name} {candidate.child_last_name}",
                    "parent_name": f"{candidate.parent_first_name} {candidate.parent_last_name}",
                    "mobile_number": candidate.mobile_number,
                    "match_score": res["score"],
                    "match_level": res["match_level"],
                    "matched_fields": res["matched_fields"]
                })

        # Sort matches by score descending
        matches.sort(key=lambda x: x["match_score"], reverse=True)

        return {
            "request_id": request_obj.id,
            "total_matches": len(matches),
            "matches": matches
        }

    @classmethod
    def get_match_details(cls, request_id: str, patient_id: str) -> dict:
        """
        Explains why a specific patient was matched against an appointment request.
        """
        request_obj = AppointmentRequest.objects.filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        patient = Patient.objects.filter(id=patient_id, is_deleted=False).first()
        if not patient:
            raise ValidationError({"patient_id": "Patient not found or inactive."})

        res = cls.calculate_match_score(request_obj, patient)

        matched_fields_detail = [
            {
                "field": "mobile_number",
                "request_value": request_obj.mobile_number,
                "patient_value": patient.mobile_number,
                "matched": "mobile_number" in res["matched_fields"]
            },
            {
                "field": "child_name",
                "request_value": f"{request_obj.child_first_name} {request_obj.child_last_name}",
                "patient_value": f"{patient.child_first_name} {patient.child_last_name}",
                "matched": "child_name" in res["matched_fields"]
            },
            {
                "field": "parent_name",
                "request_value": f"{request_obj.parent_first_name} {request_obj.parent_last_name}",
                "patient_value": f"{patient.parent_first_name} {patient.parent_last_name}",
                "matched": "parent_name" in res["matched_fields"]
            },
            {
                "field": "date_of_birth",
                "request_value": str(request_obj.date_of_birth),
                "patient_value": str(patient.date_of_birth),
                "matched": "date_of_birth" in res["matched_fields"]
            },
            {
                "field": "gender",
                "request_value": request_obj.gender,
                "patient_value": patient.gender,
                "matched": "gender" in res["matched_fields"]
            }
        ]

        return {
            "match_score": res["score"],
            "matched_fields": matched_fields_detail
        }

    @classmethod
    @transaction.atomic
    def link_patient(cls, user, ip_address: str, request_id: str, patient_id: str) -> AppointmentRequest:
        """
        Links an appointment request to an existing patient.
        """
        request_obj = AppointmentRequest.objects.filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        patient = Patient.objects.filter(id=patient_id, is_deleted=False).first()
        if not patient:
            raise ValidationError({"patient_id": "Patient not found or inactive."})

        # Request must be in PENDING or APPROVED
        allowed_statuses = [AppointmentRequestStatus.PENDING, AppointmentRequestStatus.APPROVED]
        if request_obj.status not in allowed_statuses:
            raise ValidationError({"non_field_errors": [f"Cannot link patient. Request is already in {request_obj.status} status."]})

        old_status = request_obj.status

        request_obj.patient = patient
        request_obj.status = AppointmentRequestStatus.PATIENT_LINKED
        request_obj.patient_linked_by = user
        request_obj.patient_linked_at = timezone.now()
        request_obj.save()

        # Create Timeline Entries
        PatientTimeline.objects.create(
            patient=patient,
            event="Patient Matching Started",
            description=f"Patient matching was initiated for request {request_obj.request_number}.",
            performed_by=user
        )
        PatientTimeline.objects.create(
            patient=patient,
            event="Patient Linked",
            description=f"Appointment request {request_obj.request_number} was linked to this patient.",
            performed_by=user
        )

        # Create Activity Log
        desc = f"{user.email} linked appointment request {request_obj.request_number} to Patient {patient.patient_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.PATIENT_LINKED,
            description=desc,
            ip_address=ip_address
        )

        return request_obj

    @classmethod
    def generate_patient_code(cls) -> str:
        """
        Generates a unique patient number in the format PAT-000000.
        """
        count = Patient.objects.all_with_deleted().count() + 1
        while True:
            code = f"PAT-{count:06d}"
            if not Patient.objects.all_with_deleted().filter(patient_number=code).exists():
                return code
            count += 1

    @classmethod
    @transaction.atomic
    def create_patient(cls, user, ip_address: str, request_id: str) -> Patient:
        """
        Creates a new Patient record from an appointment request after verifying no exact duplicate exists.
        """
        request_obj = AppointmentRequest.objects.filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Request must be in PENDING or APPROVED
        allowed_statuses = [AppointmentRequestStatus.PENDING, AppointmentRequestStatus.APPROVED]
        if request_obj.status not in allowed_statuses:
            raise ValidationError({"non_field_errors": [f"Cannot create patient. Request is already in {request_obj.status} status."]})

        # Run matching algorithm again to prevent duplicates
        matches_data = cls.find_matches(request_id)
        exact_matches = [m for m in matches_data["matches"] if m["match_score"] >= 95]
        if exact_matches:
            raise ValidationError({
                "non_field_errors": [
                    f"A patient with an exact match ({exact_matches[0]['child_name']}, "
                    f"{exact_matches[0]['patient_code']}) already exists in the system. "
                    "Please link to the existing patient instead."
                ]
            })

        patient_code = cls.generate_patient_code()

        # Create Patient
        patient = Patient(
            patient_number=patient_code,
            parent_first_name=request_obj.parent_first_name,
            parent_last_name=request_obj.parent_last_name,
            relationship_to_child=request_obj.relationship_to_child,
            mobile_number=request_obj.mobile_number,
            alternate_mobile_number=request_obj.alternate_mobile_number,
            email=request_obj.email,
            child_first_name=request_obj.child_first_name,
            child_last_name=request_obj.child_last_name,
            date_of_birth=request_obj.date_of_birth,
            gender=request_obj.gender,
            address="",  # Address is not in request, default to empty
            referral_source=request_obj.referral_source,
            notes=request_obj.primary_concern,
            created_by=user,
            is_deleted=False
        )
        patient.save()

        # Link Request to Patient
        request_obj.patient = patient
        request_obj.status = AppointmentRequestStatus.PATIENT_CREATED
        request_obj.patient_created_by = user
        request_obj.patient_created_at = timezone.now()
        request_obj.save()

        # Create Timeline Entries
        PatientTimeline.objects.create(
            patient=patient,
            event="Patient Matching Started",
            description=f"Patient matching was initiated for request {request_obj.request_number}.",
            performed_by=user
        )
        PatientTimeline.objects.create(
            patient=patient,
            event="New Patient Created",
            description=f"New patient record {patient.patient_number} created from request {request_obj.request_number}.",
            performed_by=user
        )

        # Create Activity Log
        desc = f"{user.email} created Patient {patient.patient_number} from appointment request {request_obj.request_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.PATIENT_CREATED,
            description=desc,
            ip_address=ip_address
        )

        return patient

    @classmethod
    def get_statistics(cls) -> dict:
        """
        Returns patient matching and creation statistics for today.
        """
        today = timezone.localdate()
        
        linked_patients = ActivityLog.objects.filter(
            action=ActivityType.PATIENT_LINKED,
            created_at__date=today
        ).count()

        new_patients = ActivityLog.objects.filter(
            action=ActivityType.PATIENT_CREATED,
            created_at__date=today
        ).count()

        # Since linking an existing patient prevents creating a duplicate, duplicate_prevented is equal to linked_patients
        duplicate_prevented = linked_patients

        # today_matches: total matching workflows processed today
        today_matches = linked_patients + new_patients

        return {
            "today_matches": today_matches,
            "linked_patients": linked_patients,
            "new_patients": new_patients,
            "duplicate_prevented": duplicate_prevented
        }
