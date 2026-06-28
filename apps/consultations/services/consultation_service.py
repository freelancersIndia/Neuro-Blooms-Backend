import os
from datetime import date
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.conf import settings

from apps.consultations.models import (
    Appointment,
    Patient,
    Consultation,
    ConsultationAttachment,
    ConsultationActivityLog,
    ConsultationAuditLog,
    AppointmentTimeline,
    PatientTimeline
)
from apps.consultations.choices import AppointmentStatus, AppointmentType
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType

def calculate_age_display(dob) -> str:
    if not dob:
        return ""
    today = date.today()
    years = today.year - dob.year
    months = today.month - dob.month
    if months < 0:
        years -= 1
        months += 12
    if years == 0:
        return f"{months} months"
    elif months == 0:
        return f"{years} years"
    else:
        return f"{years} years, {months} months"

class ConsultationService:

    @classmethod
    def validate_doctor_access(cls, user, appointment_or_consultation):
        """
        Validates that if the user is a doctor, they must be the assigned doctor.
        Admins/Super Admins/Receptionists are allowed read-only access.
        """
        assigned_doctor = (
            appointment_or_consultation.doctor 
            if isinstance(appointment_or_consultation, Appointment) 
            else appointment_or_consultation.appointment.doctor
        )
        
        if user.has_role('DOCTOR') and assigned_doctor != user:
            raise PermissionDenied("Only the assigned doctor has access to this consultation.")

    @classmethod
    def get_open_consultation_data(cls, user, appointment_id: str) -> dict:
        """
        Retrieves all required clinical data before starting a consultation.
        """
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except (Appointment.DoesNotExist, DjangoValidationError):
            raise ValidationError({"appointment_id": "Appointment does not exist."})

        cls.validate_doctor_access(user, appointment)

        if appointment.status not in [AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION]:
            raise ValidationError({
                "status": f"Appointment must be in CHECKED_IN or IN_CONSULTATION status. Current status: {appointment.status}"
            })

        patient = appointment.patient
        patient_summary = cls.get_patient_summary(patient.id)
        
        # Fetch previous consultations
        prev_consultations = Consultation.objects.filter(
            appointment__patient=patient,
            is_completed=True
        ).exclude(appointment_id=appointment_id)

        # Fetch follow-up history
        followups = prev_consultations.filter(
            appointment__appointment_type=AppointmentType.FOLLOW_UP
        )

        return {
            "appointment": appointment,
            "patient_summary": patient_summary,
            "medical_history": patient_summary.get("medical_history", {}),
            "previous_consultations": prev_consultations,
            "followups": followups,
            "appointment_information": {
                "appointment_number": appointment.appointment_number,
                "appointment_type": appointment.appointment_type,
                "appointment_date": appointment.appointment_date,
                "start_time": appointment.start_time,
                "end_time": appointment.end_time,
                "visit_reason": appointment.visit_reason
            }
        }

    @classmethod
    def get_patient_summary(cls, patient_id: str) -> dict:
        """
        Compiles a concise summary dashboard for the patient.
        """
        try:
            patient = Patient.objects.get(id=patient_id)
        except (Patient.DoesNotExist, DjangoValidationError):
            raise ValidationError({"patient_id": "Patient does not exist."})

        completed_appointments = Appointment.objects.filter(
            patient=patient,
            status=AppointmentStatus.COMPLETED
        ).order_by("-appointment_date")

        total_visits = completed_appointments.count()
        last_visit_date = completed_appointments.first().appointment_date if total_visits > 0 else None

        # Fetch completed consultations to extract previous diagnoses and treatments
        completed_consultations = Consultation.objects.filter(
            appointment__patient=patient,
            is_completed=True
        ).order_by("-created_at")

        previous_diagnoses = list(
            completed_consultations.exclude(diagnosis__isnull=True)
            .exclude(diagnosis="")
            .values_list("diagnosis", flat=True)
            .distinct()
        )

        latest_consultation = completed_consultations.first()
        current_active_treatment = (
            latest_consultation.treatment_notes if latest_consultation else None
        )

        # Retrieve primary concern from the earliest appointment or request
        first_appt = Appointment.objects.filter(patient=patient).order_by("appointment_date").first()
        primary_concern = first_appt.visit_reason if first_appt else ""

        return {
            "patient_profile": {
                "id": patient.id,
                "patient_number": patient.patient_number,
                "child_first_name": patient.child_first_name,
                "child_last_name": patient.child_last_name,
                "parent_first_name": patient.parent_first_name,
                "parent_last_name": patient.parent_last_name,
                "parent_phone": patient.mobile_number,
                "parent_email": patient.email,
                "dob": patient.date_of_birth,
                "age": calculate_age_display(patient.date_of_birth),
                "gender": patient.gender,
                "blood_group": None,  # Future-ready
                "known_allergies": None,  # Future-ready
                "medical_alerts": None,  # Future-ready
            },
            "medical_history": {
                "previous_diagnoses": previous_diagnoses,
                "current_active_treatment": current_active_treatment,
                "total_visits": total_visits,
                "last_visit": last_visit_date,
            }
        }

    @classmethod
    def get_previous_consultations(cls, patient_id: str, search_query: str = None, ordering: str = None) -> list:
        """
        Retrieves the completed consultation history for a patient.
        """
        qs = Consultation.objects.filter(
            appointment__patient_id=patient_id,
            is_completed=True
        )

        if search_query:
            qs = qs.filter(
                models.Q(diagnosis__icontains=search_query) |
                models.Q(treatment_notes__icontains=search_query) |
                models.Q(recommendations__icontains=search_query) |
                models.Q(doctor__email__icontains=search_query)
            )

        if ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-created_at")

        return qs

    @classmethod
    def get_followup_history(cls, patient_id: str) -> list:
        """
        Retrieves follow-up consultations for a patient.
        """
        return Consultation.objects.filter(
            appointment__patient_id=patient_id,
            appointment__appointment_type=AppointmentType.FOLLOW_UP,
            is_completed=True
        ).order_by("-created_at")

    @classmethod
    @transaction.atomic
    def create_consultation(cls, user, ip_address: str, appointment_id: str, data: dict) -> Consultation:
        """
        Creates a new consultation record.
        """
        try:
            appointment = Appointment.objects.get(id=appointment_id)
        except (Appointment.DoesNotExist, DjangoValidationError):
            raise ValidationError({"appointment_id": "Appointment does not exist."})

        # Only the assigned doctor can create the consultation
        if appointment.doctor != user:
            raise PermissionDenied("Only the assigned doctor can create a consultation record.")

        if appointment.status != AppointmentStatus.IN_CONSULTATION:
            raise ValidationError({
                "status": f"Appointment must be in IN_CONSULTATION status to start consultation. Current status: {appointment.status}"
            })

        # Check for duplicate consultation
        if Consultation.objects.filter(appointment=appointment).exists():
            raise ValidationError({
                "appointment_id": "A consultation record already exists for this appointment."
            })

        # Length Validations
        cls.clean_clinical_fields(data)

        # Get or create active TreatmentCase
        treatment_case = appointment.treatment_case
        if not treatment_case:
            from apps.consultations.models.treatment_case import TreatmentCase, TreatmentCaseStatus
            treatment_case = TreatmentCase.objects.filter(
                patient=appointment.patient,
                status__in=[
                    TreatmentCaseStatus.ACTIVE,
                    TreatmentCaseStatus.FOLLOW_UP_REQUIRED,
                    TreatmentCaseStatus.FOLLOW_UP_SCHEDULED,
                    TreatmentCaseStatus.FOLLOW_UP_COMPLETED
                ]
            ).first()
            
            if not treatment_case:
                treatment_case = TreatmentCase.objects.create(
                    patient=appointment.patient,
                    doctor=user,
                    status=TreatmentCaseStatus.ACTIVE,
                    primary_diagnosis=data.get("diagnosis")
                )
            
            appointment.treatment_case = treatment_case
            appointment.save(update_fields=["treatment_case"])
        elif data.get("diagnosis") and not treatment_case.primary_diagnosis:
            treatment_case.primary_diagnosis = data.get("diagnosis")
            treatment_case.save(update_fields=["primary_diagnosis"])

        consultation = Consultation(
            appointment=appointment,
            doctor=user,
            chief_complaint=data.get("chief_complaint"),
            clinical_findings=data.get("clinical_findings"),
            diagnosis=data.get("diagnosis"),
            treatment_notes=data.get("treatment_notes"),
            recommendations=data.get("recommendations"),
            is_completed=False,
            treatment_case=treatment_case,
            previous_consultation=appointment.previous_consultation
        )

        consultation.full_clean()
        consultation.save()

        # Update Timeline
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Consultation Started",
            description=f"Clinical consultation started by Dr. {user.email}.",
            performed_by=user
        )
        PatientTimeline.objects.create(
            patient=appointment.patient,
            event="Consultation Started",
            description=f"Clinical consultation started by Dr. {user.email}.",
            performed_by=user
        )

        if data.get("chief_complaint") or data.get("clinical_findings"):
            AppointmentTimeline.objects.create(
                appointment=appointment,
                event="Clinical Notes Added",
                description="Chief complaint and clinical findings recorded.",
                performed_by=user
            )

        if data.get("diagnosis"):
            AppointmentTimeline.objects.create(
                appointment=appointment,
                event="Diagnosis Recorded",
                description=f"Diagnosis recorded: {data.get('diagnosis')}.",
                performed_by=user
            )

        if data.get("treatment_notes") or data.get("recommendations"):
            AppointmentTimeline.objects.create(
                appointment=appointment,
                event="Treatment Updated",
                description="Treatment notes and recommendations updated.",
                performed_by=user
            )

        # Logs
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CONSULTATION_CREATED,
            description=f"Dr. {user.email} created consultation {consultation.id} for appointment {appointment.appointment_number}.",
            ip_address=ip_address
        )

        ConsultationActivityLog.objects.create(
            doctor=user,
            patient=appointment.patient,
            consultation=consultation,
            appointment=appointment,
            action=ActivityType.CONSULTATION_CREATED,
            new_values=data,
            ip_address=ip_address
        )

        return consultation

    @classmethod
    @transaction.atomic
    def update_consultation(cls, user, ip_address: str, consultation_id: str, data: dict) -> Consultation:
        """
        Updates an active consultation record.
        """
        try:
            consultation = Consultation.objects.get(id=consultation_id)
        except (Consultation.DoesNotExist, DjangoValidationError):
            raise ValidationError({"consultation_id": "Consultation does not exist."})

        # Only the assigned doctor can edit
        if consultation.doctor != user:
            raise PermissionDenied("Only the assigned doctor can edit this consultation.")

        if consultation.is_completed:
            raise ValidationError({"status": "Completed consultations cannot be modified."})

        # Length Validations
        cls.clean_clinical_fields(data)

        # Capture old values for audit logging
        old_values = {
            "chief_complaint": consultation.chief_complaint,
            "clinical_findings": consultation.clinical_findings,
            "diagnosis": consultation.diagnosis,
            "treatment_notes": consultation.treatment_notes,
            "recommendations": consultation.recommendations,
        }

        # Apply updates
        editable_fields = ["chief_complaint", "clinical_findings", "diagnosis", "treatment_notes", "recommendations"]
        for field in editable_fields:
            if field in data:
                setattr(consultation, field, data[field])

        consultation.full_clean()
        consultation.save()

        # Log changes and create audit entries
        new_values = {
            "chief_complaint": consultation.chief_complaint,
            "clinical_findings": consultation.clinical_findings,
            "diagnosis": consultation.diagnosis,
            "treatment_notes": consultation.treatment_notes,
            "recommendations": consultation.recommendations,
        }

        changed_fields = []
        for field, old_val in old_values.items():
            new_val = new_values[field]
            if old_val != new_val:
                changed_fields.append(field)
                # Save Audit Log
                ConsultationAuditLog.objects.create(
                    consultation=consultation,
                    field_name=field,
                    old_value=old_val,
                    new_value=new_val,
                    modified_by=user
                )

        if changed_fields:
            # Update Timeline
            appointment = consultation.appointment
            if "chief_complaint" in changed_fields or "clinical_findings" in changed_fields:
                AppointmentTimeline.objects.create(
                    appointment=appointment,
                    event="Clinical Notes Added",
                    description="Clinical notes updated.",
                    performed_by=user
                )
            if "diagnosis" in changed_fields:
                AppointmentTimeline.objects.create(
                    appointment=appointment,
                    event="Diagnosis Recorded",
                    description=f"Diagnosis updated: {consultation.diagnosis}.",
                    performed_by=user
                )
            if "treatment_notes" in changed_fields or "recommendations" in changed_fields:
                AppointmentTimeline.objects.create(
                    appointment=appointment,
                    event="Treatment Updated",
                    description="Treatment and recommendations updated.",
                    performed_by=user
                )

            # Activity Logs
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.CONSULTATION_UPDATED,
                description=f"Dr. {user.email} updated consultation {consultation.id}. Changed fields: {', '.join(changed_fields)}.",
                ip_address=ip_address
            )

            ConsultationActivityLog.objects.create(
                doctor=user,
                patient=appointment.patient,
                consultation=consultation,
                appointment=appointment,
                action=ActivityType.CONSULTATION_UPDATED,
                old_values={f: old_values[f] for f in changed_fields},
                new_values={f: new_values[f] for f in changed_fields},
                ip_address=ip_address
            )

        return consultation

    @classmethod
    @transaction.atomic
    def upload_attachments(cls, user, ip_address: str, consultation_id: str, files: list) -> list:
        """
        Uploads supporting documents to the consultation.
        """
        try:
            consultation = Consultation.objects.get(id=consultation_id)
        except (Consultation.DoesNotExist, DjangoValidationError):
            raise ValidationError({"consultation_id": "Consultation does not exist."})

        if consultation.doctor != user:
            raise PermissionDenied("Only the assigned doctor can upload documents.")

        if consultation.is_completed:
            raise ValidationError({"status": "Cannot upload documents to a completed consultation."})

        allowed_extensions = {".pdf", ".doc", ".docx", ".png", ".jpg", ".jpeg", ".webp"}
        max_size = 20 * 1024 * 1024  # 20 MB

        attachments = []
        for file in files:
            ext = os.path.splitext(file.name)[1].lower()
            if ext not in allowed_extensions:
                raise ValidationError({"file": f"Unsupported file extension: {ext}. Allowed: PDF, DOC, DOCX, PNG, JPG, JPEG, WEBP."})
            
            if file.size > max_size:
                raise ValidationError({"file": f"File size exceeds 20 MB limit: {file.name}."})

            attachment = ConsultationAttachment(
                consultation=consultation,
                uploaded_by=user,
                file=file,
                original_name=file.name,
                file_size=file.size,
                mime_type=file.content_type
            )
            attachment.full_clean()
            attachment.save()
            attachments.append(attachment)

            # Update Timeline
            AppointmentTimeline.objects.create(
                appointment=consultation.appointment,
                event="Document Uploaded",
                description=f"Clinical document uploaded: {file.name}.",
                performed_by=user
            )
            PatientTimeline.objects.create(
                patient=consultation.appointment.patient,
                event="Document Uploaded",
                description=f"Clinical document uploaded: {file.name}.",
                performed_by=user
            )

            # Logs
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.CONSULTATION_ATTACHMENT_UPLOADED,
                description=f"Dr. {user.email} uploaded document {file.name} to consultation {consultation.id}.",
                ip_address=ip_address
            )

            ConsultationActivityLog.objects.create(
                doctor=user,
                patient=consultation.appointment.patient,
                consultation=consultation,
                appointment=consultation.appointment,
                action=ActivityType.CONSULTATION_ATTACHMENT_UPLOADED,
                new_values={"file": file.name, "size": file.size},
                ip_address=ip_address
            )

        return attachments

    @classmethod
    def list_attachments(cls, user, consultation_id: str) -> list:
        """
        Lists all active attachments for the consultation.
        """
        try:
            consultation = Consultation.objects.get(id=consultation_id)
        except (Consultation.DoesNotExist, DjangoValidationError):
            raise ValidationError({"consultation_id": "Consultation does not exist."})

        cls.validate_doctor_access(user, consultation)

        return ConsultationAttachment.objects.filter(
            consultation=consultation,
            is_active=True
        )

    @classmethod
    @transaction.atomic
    def delete_attachment(cls, user, ip_address: str, consultation_id: str, attachment_id: str):
        """
        Soft deletes an attachment.
        """
        try:
            attachment = ConsultationAttachment.objects.get(
                id=attachment_id,
                consultation_id=consultation_id,
                is_active=True
            )
        except (ConsultationAttachment.DoesNotExist, DjangoValidationError):
            raise ValidationError({"attachment_id": "Attachment does not exist."})

        consultation = attachment.consultation

        if consultation.doctor != user:
            raise PermissionDenied("Only the assigned doctor can delete documents.")

        if consultation.is_completed:
            raise ValidationError({"status": "Cannot delete documents from a completed consultation."})

        attachment.is_active = False
        attachment.save()

        # Update Timeline
        AppointmentTimeline.objects.create(
            appointment=consultation.appointment,
            event="Document Deleted",
            description=f"Clinical document deleted: {attachment.original_name}.",
            performed_by=user
        )

        # Logs
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CONSULTATION_ATTACHMENT_DELETED,
            description=f"Dr. {user.email} deleted document {attachment.original_name} from consultation {consultation.id}.",
            ip_address=ip_address
        )

        ConsultationActivityLog.objects.create(
            doctor=user,
            patient=consultation.appointment.patient,
            consultation=consultation,
            appointment=consultation.appointment,
            action=ActivityType.CONSULTATION_ATTACHMENT_DELETED,
            old_values={"file": attachment.original_name},
            ip_address=ip_address
        )

    @classmethod
    @transaction.atomic
    def complete_consultation(cls, user, ip_address: str, consultation_id: str) -> Consultation:
        """
        Completes and locks a clinical consultation.
        """
        try:
            consultation = Consultation.objects.get(id=consultation_id)
        except (Consultation.DoesNotExist, DjangoValidationError):
            raise ValidationError({"consultation_id": "Consultation does not exist."})

        if consultation.doctor != user:
            raise PermissionDenied("Only the assigned doctor can complete this consultation.")

        if consultation.is_completed:
            raise ValidationError({"status": "Consultation is already completed."})

        # Validations before completion
        if not consultation.diagnosis or not consultation.diagnosis.strip():
            raise ValidationError({"diagnosis": "Diagnosis is required before completing the consultation."})

        if not consultation.treatment_notes or not consultation.treatment_notes.strip():
            raise ValidationError({"treatment_notes": "Treatment Notes are required before completing the consultation."})

        if not consultation.recommendations or not consultation.recommendations.strip():
            raise ValidationError({"recommendations": "Recommendations are required before completing the consultation."})

        # Lock and complete
        consultation.is_completed = True
        consultation.save()

        # Transition Appointment status
        appointment = consultation.appointment
        appointment.status = AppointmentStatus.COMPLETED
        appointment.save()

        # Update Timeline
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Consultation Completed",
            description=f"Consultation completed by Dr. {user.email}. Appointment status changed to COMPLETED.",
            performed_by=user
        )
        PatientTimeline.objects.create(
            patient=appointment.patient,
            event="Consultation Completed",
            description=f"Consultation completed by Dr. {user.email}.",
            performed_by=user
        )

        # Logs
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.CONSULTATION_COMPLETED,
            description=f"Dr. {user.email} completed consultation {consultation.id}.",
            ip_address=ip_address
        )

        ConsultationActivityLog.objects.create(
            doctor=user,
            patient=appointment.patient,
            consultation=consultation,
            appointment=appointment,
            action=ActivityType.CONSULTATION_COMPLETED,
            ip_address=ip_address
        )

        return consultation

    @classmethod
    def clean_clinical_fields(cls, data):
        """
        Validates maximum lengths of clinical fields.
        """
        limits = {
            "chief_complaint": 2000,
            "clinical_findings": 10000,
            "diagnosis": 3000,
            "treatment_notes": 10000,
            "recommendations": 5000,
        }

        errors = {}
        for field, max_len in limits.items():
            value = data.get(field)
            if value and len(value) > max_len:
                errors[field] = f"This field cannot exceed {max_len} characters."

        if errors:
            raise ValidationError(errors)
