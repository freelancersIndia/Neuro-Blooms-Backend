import uuid
from datetime import date, time, datetime, timedelta
from django.db import transaction
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError, PermissionDenied
from django.conf import settings

from apps.consultations.models import (
    Appointment,
    Patient,
    Consultation,
    TreatmentCase,
    ConsultationAttachment,
    ConsultationActivityLog,
    ConsultationAuditLog,
    AppointmentTimeline,
    PatientTimeline
)
from apps.consultations.models.treatment_case import TreatmentCaseStatus
from apps.consultations.choices import AppointmentStatus, AppointmentType, BookingSource
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.services.appointment_service import AppointmentService

class FollowupService:

    @classmethod
    @transaction.atomic
    def record_followup_decision(cls, user, ip_address: str, consultation_id: str, requires_followup: bool) -> dict:
        """
        Doctor decides if follow-up is required or treatment is complete.
        """
        try:
            consultation = Consultation.objects.get(id=consultation_id)
        except (Consultation.DoesNotExist, DjangoValidationError):
            raise ValidationError({"consultation_id": "Consultation record does not exist."})

        # Only the assigned doctor can record follow-up decision
        if consultation.doctor != user:
            raise PermissionDenied("Only the assigned doctor can record a follow-up decision.")

        # Consultation must be completed
        if not consultation.is_completed:
            raise ValidationError({"status": "Only completed consultations can have a follow-up decision recorded."})

        # Cannot execute twice
        if consultation.requires_followup is not None:
            raise ValidationError({"requires_followup": "Follow-up decision has already been recorded for this consultation."})

        consultation.requires_followup = requires_followup
        consultation.save(update_fields=["requires_followup"])

        treatment_case = consultation.treatment_case

        if not requires_followup:
            if treatment_case:
                treatment_case.status = TreatmentCaseStatus.CASE_CLOSED
                treatment_case.end_date = date.today()
                treatment_case.save(update_fields=["status", "end_date"])

            # Create Timeline
            PatientTimeline.objects.create(
                patient=consultation.appointment.patient,
                event="Treatment Completed",
                description=f"Treatment completed and case closed by Dr. {user.email}.",
                performed_by=user
            )
            AppointmentTimeline.objects.create(
                appointment=consultation.appointment,
                event="Treatment Completed",
                description=f"Treatment completed and case closed by Dr. {user.email}.",
                performed_by=user
            )

            # Log Activity
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.FOLLOW_UP_DECISION_RECORDED,
                ip_address=ip_address,
                description=f"Doctor recorded treatment completed. Case closed for patient {consultation.appointment.patient.id}."
            )
            return {"message": "Case Closed.", "requires_followup": False}

        else:
            if treatment_case:
                treatment_case.status = TreatmentCaseStatus.FOLLOW_UP_REQUIRED
                treatment_case.save(update_fields=["status"])

            # Create Timeline
            PatientTimeline.objects.create(
                patient=consultation.appointment.patient,
                event="Follow-up Required",
                description=f"Follow-up appointment recommended by Dr. {user.email}.",
                performed_by=user
            )
            AppointmentTimeline.objects.create(
                appointment=consultation.appointment,
                event="Follow-up Required",
                description=f"Follow-up appointment recommended by Dr. {user.email}.",
                performed_by=user
            )

            # Log Activity
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.FOLLOW_UP_DECISION_RECORDED,
                ip_address=ip_address,
                description=f"Doctor recorded follow-up required for patient {consultation.appointment.patient.id}."
            )
            return {"message": "Ready to create follow-up.", "requires_followup": True}

    @classmethod
    @transaction.atomic
    def create_followup(cls, user, ip_address: str, data: dict) -> Appointment:
        """
        Creates a follow-up appointment directly in CONFIRMED status.
        """
        consultation_id = data.get("consultation_id")
        doctor_id = data.get("doctor_id")
        followup_date = data.get("followup_date")
        start_time = data.get("start_time")
        reason = data.get("reason", "Review speech improvement")
        notes = data.get("notes", "")

        # Parsings
        if isinstance(followup_date, str):
            followup_date = datetime.strptime(followup_date, "%Y-%m-%d").date()
        if isinstance(start_time, str):
            start_time = datetime.strptime(start_time, "%H:%M").time()

        if followup_date < date.today():
            raise ValidationError({"followup_date": "Follow-up date cannot be in the past."})

        try:
            consultation = Consultation.objects.get(id=consultation_id)
        except (Consultation.DoesNotExist, DjangoValidationError):
            raise ValidationError({"consultation_id": "Consultation record does not exist."})

        # Consultation must be completed
        if not consultation.is_completed:
            raise ValidationError({"consultation_id": "Consultation must be completed to schedule a follow-up."})

        # Only the assigned doctor can schedule follow-up
        if consultation.doctor != user:
            raise PermissionDenied("Only the assigned doctor can schedule a follow-up.")

        patient = consultation.appointment.patient
        if not patient.is_active:
            raise ValidationError({"patient": "Patient record is inactive."})

        # Cannot create follow-up after case closed
        treatment_case = consultation.treatment_case
        if treatment_case and treatment_case.status == TreatmentCaseStatus.CASE_CLOSED:
            raise ValidationError({"treatment_case": "Cannot create follow-up after case closed."})

        # Cannot create follow-up for cancelled consultation
        if consultation.appointment.status == AppointmentStatus.CANCELLED:
            raise ValidationError({"consultation_id": "Cannot create follow-up for a cancelled consultation."})

        # Cannot create duplicate follow-up
        if Appointment.objects.filter(previous_consultation=consultation).exists():
            raise ValidationError({"consultation_id": "A follow-up appointment has already been created for this consultation."})

        # Validate slot availability
        validation = AppointmentService.validate_slot(doctor_id, followup_date, start_time)
        if not validation.get("valid"):
            raise ValidationError({"start_time": f"Requested slot is not available: {validation.get('reason', 'Slot already booked')}"})

        # Generate Appointment Number
        unique_suffix = uuid.uuid4().hex[:6].upper()
        appointment_number = f"APT-{followup_date.strftime('%Y%m%d')}-{unique_suffix}"

        # Calculate End Time (default 30 mins)
        start_datetime = datetime.combine(followup_date, start_time)
        end_time = (start_datetime + timedelta(minutes=30)).time()

        # Create Confirmed Appointment
        appointment = Appointment.objects.create(
            appointment_number=appointment_number,
            patient=patient,
            doctor_id=doctor_id,
            status=AppointmentStatus.CONFIRMED,
            appointment_type=AppointmentType.FOLLOW_UP,
            booking_source=BookingSource.ADMIN_PANEL,
            appointment_date=followup_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=30,
            visit_reason=reason,
            internal_notes=notes,
            treatment_case=treatment_case,
            previous_consultation=consultation,
            approved_by=user,
            created_by=user
        )

        # Update TreatmentCase status
        if treatment_case:
            treatment_case.status = TreatmentCaseStatus.FOLLOW_UP_SCHEDULED
            treatment_case.save(update_fields=["status"])

        # Create Timelines
        PatientTimeline.objects.create(
            patient=patient,
            event="Follow-up Created",
            description=f"Follow-up appointment {appointment_number} scheduled for {followup_date} at {start_time.strftime('%H:%M')}.",
            performed_by=user
        )
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Follow-up Created",
            description=f"Follow-up appointment scheduled by Dr. {user.email}.",
            performed_by=user
        )

        # Log Activity
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.FOLLOW_UP_CREATED,
            ip_address=ip_address,
            description=f"Doctor scheduled follow-up appointment {appointment_number}."
        )

        return appointment

    @classmethod
    def get_followup_details(cls, user, appointment_id: str) -> dict:
        """
        Retrieves complete follow-up information.
        """
        try:
            appointment = Appointment.objects.get(id=appointment_id, appointment_type=AppointmentType.FOLLOW_UP)
        except (Appointment.DoesNotExist, DjangoValidationError):
            raise ValidationError({"appointment_id": "Follow-up appointment does not exist."})

        prev_consultation = appointment.previous_consultation

        return {
            "appointment": appointment,
            "patient": appointment.patient,
            "doctor": appointment.doctor,
            "previous_consultation": prev_consultation,
            "previous_diagnosis": prev_consultation.diagnosis if prev_consultation else None,
            "previous_treatment": prev_consultation.treatment_notes if prev_consultation else None,
            "reason": appointment.visit_reason,
            "notes": appointment.internal_notes,
            "upcoming_appointment": {
                "appointment_number": appointment.appointment_number,
                "appointment_date": appointment.appointment_date,
                "start_time": appointment.start_time,
                "status": appointment.status
            }
        }

    @classmethod
    def get_patient_followups(cls, patient_id: str, filters: dict = None, ordering: str = None):
        """
        Returns all follow-up appointments for a patient.
        """
        qs = Appointment.objects.filter(patient_id=patient_id, appointment_type=AppointmentType.FOLLOW_UP)

        if filters:
            doctor_id = filters.get("doctor")
            start_date = filters.get("start_date")
            end_date = filters.get("end_date")

            if doctor_id:
                qs = qs.filter(doctor_id=doctor_id)
            if start_date:
                qs = qs.filter(appointment_date__gte=start_date)
            if end_date:
                qs = qs.filter(appointment_date__lte=end_date)

        if ordering:
            qs = qs.order_by(ordering)
        else:
            qs = qs.order_by("-appointment_date", "-start_time")

        return qs

    @classmethod
    @transaction.atomic
    def update_followup(cls, user, ip_address: str, appointment_id: str, data: dict) -> Appointment:
        """
        Updates follow-up details (date, time, reason, notes).
        """
        try:
            appointment = Appointment.objects.get(id=appointment_id, appointment_type=AppointmentType.FOLLOW_UP)
        except (Appointment.DoesNotExist, DjangoValidationError):
            raise ValidationError({"appointment_id": "Follow-up appointment does not exist."})

        # Only the assigned doctor can edit details
        if appointment.doctor != user:
            raise PermissionDenied("Only the assigned doctor can edit follow-up details.")

        # Validate status
        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise ValidationError({"status": f"Cannot update a follow-up appointment that is {appointment.status}."})

        # Extract fields
        new_date = data.get("appointment_date")
        new_time = data.get("start_time")
        new_reason = data.get("reason")
        new_notes = data.get("notes")

        if isinstance(new_date, str):
            new_date = datetime.strptime(new_date, "%Y-%m-%d").date()
        if isinstance(new_time, str):
            new_time = datetime.strptime(new_time, "%H:%M").time()

        date_changed = new_date and new_date != appointment.appointment_date
        time_changed = new_time and new_time != appointment.start_time

        # Validate slot if date or time changes
        if date_changed or time_changed:
            chk_date = new_date or appointment.appointment_date
            chk_time = new_time or appointment.start_time
            if chk_date < date.today():
                raise ValidationError({"appointment_date": "Follow-up date cannot be in the past."})

            validation = AppointmentService.validate_slot(
                appointment.doctor.id,
                chk_date,
                chk_time,
                exclude_appointment_id=appointment.id
            )
            if not validation.get("valid"):
                raise ValidationError({"start_time": f"Requested slot is not available: {validation.get('reason', 'Slot already booked')}"})

            # Update end time
            start_datetime = datetime.combine(chk_date, chk_time)
            appointment.end_time = (start_datetime + timedelta(minutes=30)).time()

        # Audit logs & updates
        audit_logs = []
        fields_to_update = []

        if date_changed:
            audit_logs.append(ConsultationAuditLog(
                consultation=appointment.previous_consultation,
                field_name="followup_date",
                old_value=str(appointment.appointment_date),
                new_value=str(new_date),
                modified_by=user
            ))
            appointment.appointment_date = new_date
            fields_to_update.append("appointment_date")
            fields_to_update.append("end_time")

        if time_changed:
            audit_logs.append(ConsultationAuditLog(
                consultation=appointment.previous_consultation,
                field_name="start_time",
                old_value=appointment.start_time.strftime("%H:%M"),
                new_value=new_time.strftime("%H:%M"),
                modified_by=user
            ))
            appointment.start_time = new_time
            fields_to_update.append("start_time")
            fields_to_update.append("end_time")

        if new_reason and new_reason != appointment.visit_reason:
            audit_logs.append(ConsultationAuditLog(
                consultation=appointment.previous_consultation,
                field_name="visit_reason",
                old_value=appointment.visit_reason or "",
                new_value=new_reason,
                modified_by=user
            ))
            appointment.visit_reason = new_reason
            fields_to_update.append("visit_reason")

        if new_notes is not None and new_notes != appointment.internal_notes:
            audit_logs.append(ConsultationAuditLog(
                consultation=appointment.previous_consultation,
                field_name="notes",
                old_value=appointment.internal_notes or "",
                new_value=new_notes,
                modified_by=user
            ))
            appointment.internal_notes = new_notes
            fields_to_update.append("internal_notes")

        if fields_to_update:
            appointment.save(update_fields=fields_to_update)
            if audit_logs and appointment.previous_consultation:
                ConsultationAuditLog.objects.bulk_create(audit_logs)

            # Create Timelines
            desc_changes = ", ".join(fields_to_update)
            PatientTimeline.objects.create(
                patient=appointment.patient,
                event="Follow-up Updated",
                description=f"Follow-up appointment {appointment.appointment_number} details updated ({desc_changes}).",
                performed_by=user
            )
            AppointmentTimeline.objects.create(
                appointment=appointment,
                event="Follow-up Updated",
                description=f"Follow-up appointment details updated by Dr. {user.email}.",
                performed_by=user
            )

            # Log Activity
            ActivityLog.objects.create(
                user=user,
                action=ActivityType.FOLLOW_UP_UPDATED,
                ip_address=ip_address,
                description=f"Doctor updated follow-up appointment {appointment.appointment_number}."
            )

        return appointment

    @classmethod
    @transaction.atomic
    def cancel_followup(cls, user, ip_address: str, appointment_id: str, reason: str) -> Appointment:
        """
        Cancels a follow-up appointment.
        """
        if not reason:
            raise ValidationError({"reason": "Cancellation reason is required."})

        try:
            appointment = Appointment.objects.get(id=appointment_id, appointment_type=AppointmentType.FOLLOW_UP)
        except (Appointment.DoesNotExist, DjangoValidationError):
            raise ValidationError({"appointment_id": "Follow-up appointment does not exist."})

        # Only the assigned doctor can cancel
        if appointment.doctor != user:
            raise PermissionDenied("Only the assigned doctor can cancel this follow-up.")

        # Validate status
        if appointment.status in [AppointmentStatus.COMPLETED, AppointmentStatus.CANCELLED, AppointmentStatus.NO_SHOW]:
            raise ValidationError({"status": f"Cannot cancel a follow-up appointment that is {appointment.status}."})

        appointment.status = AppointmentStatus.CANCELLED
        appointment.internal_notes = f"{appointment.internal_notes or ''}\n[Cancelled by Doctor. Reason: {reason}]".strip()
        appointment.save(update_fields=["status", "internal_notes"])

        # Update TreatmentCase status back to FOLLOW_UP_REQUIRED
        treatment_case = appointment.treatment_case
        if treatment_case:
            treatment_case.status = TreatmentCaseStatus.FOLLOW_UP_REQUIRED
            treatment_case.save(update_fields=["status"])

        # Create Timelines
        PatientTimeline.objects.create(
            patient=appointment.patient,
            event="Follow-up Cancelled",
            description=f"Follow-up appointment {appointment.appointment_number} cancelled. Reason: {reason}",
            performed_by=user
        )
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Follow-up Cancelled",
            description=f"Follow-up appointment cancelled by Dr. {user.email}. Reason: {reason}",
            performed_by=user
        )

        # Log Activity
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.FOLLOW_UP_CANCELLED,
            ip_address=ip_address,
            description=f"Doctor cancelled follow-up appointment {appointment.appointment_number}."
        )

        return appointment

    @classmethod
    def get_treatment_case(cls, patient_id: str) -> dict:
        """
        Compiles the complete treatment journey for a patient.
        """
        treatment_case = TreatmentCase.objects.filter(patient_id=patient_id).first()
        if not treatment_case:
            raise ValidationError({"patient_id": "No treatment case found for this patient."})

        consultations = treatment_case.consultations.all().order_by("created_at")
        followups = treatment_case.appointments.filter(appointment_type=AppointmentType.FOLLOW_UP).order_by("appointment_date", "start_time")

        # Initial consultation
        initial_consultation = consultations.filter(previous_consultation__isnull=True).first()

        # Documents
        attachments = ConsultationAttachment.objects.filter(
            consultation__in=consultations,
            is_active=True
        )

        # Timeline
        timeline_events = PatientTimeline.objects.filter(patient_id=patient_id).order_by("created_at")

        # Duration
        end = treatment_case.end_date or date.today()
        duration_days = (end - treatment_case.start_date).days

        # Next Appointment
        next_appointment = treatment_case.appointments.filter(
            status=AppointmentStatus.CONFIRMED,
            appointment_date__gte=date.today()
        ).order_by("appointment_date", "start_time").first()

        return {
            "patient": treatment_case.patient,
            "treatment_case_id": treatment_case.id,
            "status": treatment_case.status,
            "primary_diagnosis": treatment_case.primary_diagnosis,
            "doctor": treatment_case.doctor,
            "initial_consultation": initial_consultation,
            "consultations": consultations,
            "followups": followups,
            "uploaded_documents": attachments,
            "timeline": timeline_events,
            "case_duration_days": duration_days,
            "next_appointment": next_appointment
        }

    @classmethod
    @transaction.atomic
    def close_treatment_case(cls, user, ip_address: str, patient_id: str, closing_summary: str, outcome: str) -> TreatmentCase:
        """
        Closes the active treatment case.
        """
        if not closing_summary:
            raise ValidationError({"closing_summary": "Closing summary is required to close the treatment case."})
        if not outcome:
            raise ValidationError({"outcome": "Outcome is required to close the treatment case."})

        try:
            treatment_case = TreatmentCase.objects.get(
                patient_id=patient_id,
                status__in=[
                    TreatmentCaseStatus.ACTIVE,
                    TreatmentCaseStatus.FOLLOW_UP_REQUIRED,
                    TreatmentCaseStatus.FOLLOW_UP_SCHEDULED,
                    TreatmentCaseStatus.FOLLOW_UP_COMPLETED
                ]
            )
        except TreatmentCase.DoesNotExist:
            raise ValidationError({"patient_id": "No active treatment case found for this patient."})

        # Only the assigned doctor can close
        if treatment_case.doctor != user:
            raise PermissionDenied("Only the assigned doctor can close this treatment case.")

        # Check for pending or future appointments
        pending_exists = Appointment.objects.filter(
            patient_id=patient_id,
            status__in=[AppointmentStatus.CHECKED_IN, AppointmentStatus.IN_CONSULTATION]
        ).exists()

        future_exists = Appointment.objects.filter(
            patient_id=patient_id,
            status=AppointmentStatus.CONFIRMED,
            appointment_date__gte=date.today()
        ).exists()

        if pending_exists or future_exists:
            raise ValidationError({"patient_id": "Cannot close treatment case while future or pending appointments exist."})

        treatment_case.status = TreatmentCaseStatus.CASE_CLOSED
        treatment_case.closing_summary = closing_summary
        treatment_case.outcome = outcome
        treatment_case.end_date = date.today()
        treatment_case.save(update_fields=["status", "closing_summary", "outcome", "end_date"])

        # Create Timeline
        PatientTimeline.objects.create(
            patient=treatment_case.patient,
            event="Treatment Closed",
            description=f"Treatment case closed by Dr. {user.email}. Outcome: {outcome}.",
            performed_by=user
        )

        # Log Activity
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.TREATMENT_CASE_CLOSED,
            ip_address=ip_address,
            description=f"Doctor closed treatment case for patient {patient_id}. Outcome: {outcome}."
        )

        return treatment_case

    @classmethod
    @transaction.atomic
    def reopen_treatment_case(cls, user, ip_address: str, patient_id: str, reason: str) -> TreatmentCase:
        """
        Reopens a previously closed treatment case.
        """
        if not reason:
            raise ValidationError({"reason": "Reopen reason is required."})

        # Check if there is already an active treatment case
        active_exists = TreatmentCase.objects.filter(
            patient_id=patient_id,
            status__in=[
                TreatmentCaseStatus.ACTIVE,
                TreatmentCaseStatus.FOLLOW_UP_REQUIRED,
                TreatmentCaseStatus.FOLLOW_UP_SCHEDULED,
                TreatmentCaseStatus.FOLLOW_UP_COMPLETED
            ]
        ).exists()

        if active_exists:
            raise ValidationError({"patient_id": "Patient already has an active treatment case."})

        # Get latest closed case
        try:
            treatment_case = TreatmentCase.objects.filter(
                patient_id=patient_id,
                status=TreatmentCaseStatus.CASE_CLOSED
            ).order_by("-created_at").first()
            if not treatment_case:
                raise TreatmentCase.DoesNotExist()
        except TreatmentCase.DoesNotExist:
            raise ValidationError({"patient_id": "No closed treatment case found for this patient."})

        # Only the assigned doctor can reopen
        if treatment_case.doctor != user:
            raise PermissionDenied("Only the assigned doctor can reopen this treatment case.")

        treatment_case.status = TreatmentCaseStatus.ACTIVE
        treatment_case.reopen_reason = reason
        treatment_case.end_date = None
        treatment_case.save(update_fields=["status", "reopen_reason", "end_date"])

        # Create Timeline
        PatientTimeline.objects.create(
            patient=treatment_case.patient,
            event="Treatment Reopened",
            description=f"Treatment case reopened by Dr. {user.email}. Reason: {reason}.",
            performed_by=user
        )

        # Log Activity
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.TREATMENT_CASE_REOPENED,
            ip_address=ip_address,
            description=f"Doctor reopened treatment case for patient {patient_id}. Reason: {reason}."
        )

        return treatment_case
