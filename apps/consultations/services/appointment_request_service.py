import datetime
import uuid
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Avg, F, Q, ExpressionWrapper, fields, Value, CharField, Exists, OuterRef
from django.db.models.functions import Concat
from rest_framework.exceptions import ValidationError

from apps.accounts.models.user import User
from apps.accounts.models.activity_log import ActivityLog
from apps.accounts.constants.activity_types import ActivityType
from apps.consultations.models import (
    AppointmentRequest,
    Patient,
    Appointment,
    AppointmentTimeline,
    PatientTimeline,
    AppointmentStatusHistory,
    ClinicSettings,
    ClinicWeeklySchedule,
    ClinicHoliday,
    ClinicBreak,
    DoctorAvailability,
    DoctorWorkingDay,
    DoctorLeave,
    DoctorBlockedSlot,
    AppointmentRequestTimeline,
    AppointmentRequestActivityLog
)
from apps.consultations.choices import (
    AppointmentRequestStatus,
    AppointmentStatus,
    AppointmentType,
    BookingSource,
    Weekday,
    Gender,
    RelationshipToChild,
    AppointmentRequestTimelineEvent
)

class AppointmentRequestService:

    @classmethod
    def log_timeline(cls, appointment_request, event_code, title, description, performed_by=None, metadata=None, icon=None, color=None):
        return AppointmentRequestTimeline.objects.create(
            appointment_request=appointment_request,
            event_code=event_code,
            title=title,
            description=description,
            performed_by=performed_by,
            metadata=metadata or {},
            icon=icon,
            color=color
        )

    @classmethod
    def log_activity(cls, appointment_request, action, performed_by, old_values=None, new_values=None, ip_address=None, browser=None, user_agent=None, booking_source=None):
        return AppointmentRequestActivityLog.objects.create(
            appointment_request=appointment_request,
            action=action,
            performed_by=performed_by,
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            browser=browser,
            user_agent=user_agent,
            booking_source=booking_source or appointment_request.booking_source
        )

    @classmethod
    @transaction.atomic
    def log_view(cls, user, ip_address, request_id, user_agent=None, browser=None):
        request_obj = AppointmentRequest.objects.filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Prevent duplicate view logs within same authenticated session (same user within 5 minutes)
        five_minutes_ago = timezone.now() - datetime.timedelta(minutes=5)
        recent_view = AppointmentRequestTimeline.objects.filter(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.VIEWED,
            performed_by=user,
            created_at__gte=five_minutes_ago
        ).exists()

        if not recent_view:
            cls.log_timeline(
                appointment_request=request_obj,
                event_code=AppointmentRequestTimelineEvent.VIEWED,
                title="Viewed",
                description=f"Request was viewed by {user.email}",
                performed_by=user,
                icon="visibility",
                color="blue"
            )
            cls.log_activity(
                appointment_request=request_obj,
                action="Viewed",
                performed_by=user,
                ip_address=ip_address,
                browser=browser,
                user_agent=user_agent,
                old_values=None,
                new_values=None
            )
        return request_obj

    @classmethod
    def build_action_metadata(cls, request_obj) -> dict:
        has_patient = request_obj.patient_id is not None
        
        # Check if converted: has an active confirmed/checked-in/completed/in-consultation/rescheduled appointment
        has_appt = request_obj.appointments.filter(
            is_active=True,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED,
                AppointmentStatus.RESCHEDULED
            ]
        ).exists()
        status_val = request_obj.status

        # can_approve: Status is PENDING, PATIENT_LINKED, PATIENT_CREATED, or RESCHEDULED, and has patient, and not converted
        can_approve = (
            status_val in [
                AppointmentRequestStatus.PENDING,
                AppointmentRequestStatus.PATIENT_LINKED,
                AppointmentRequestStatus.PATIENT_CREATED,
                AppointmentRequestStatus.RESCHEDULED
            ]
            and has_patient
            and not has_appt
        )

        # can_reject: Not already approved or rejected, and not converted
        can_reject = (
            status_val not in [
                AppointmentRequestStatus.APPROVED,
                AppointmentRequestStatus.REJECTED
            ]
            and not has_appt
        )

        # can_create_patient: No patient linked, not rejected, not converted
        can_create_patient = (
            not has_patient
            and status_val != AppointmentRequestStatus.REJECTED
            and not has_appt
        )

        # can_link_patient: No patient linked, not rejected, not converted
        can_link_patient = (
            not has_patient
            and status_val != AppointmentRequestStatus.REJECTED
            and not has_appt
        )

        # can_convert: Status is APPROVED, patient linked, and not already converted
        can_convert = (
            status_val == AppointmentRequestStatus.APPROVED
            and has_patient
            and not has_appt
        )

        # can_print: Always allowed
        can_print = True

        # can_edit: Status is PENDING or RESCHEDULED, and not converted
        can_edit = (
            status_val in [
                AppointmentRequestStatus.PENDING,
                AppointmentRequestStatus.RESCHEDULED
            ]
            and not has_appt
        )

        return {
            "can_approve": can_approve,
            "can_reject": can_reject,
            "can_create_patient": can_create_patient,
            "can_link_patient": can_link_patient,
            "can_convert": can_convert,
            "can_print": can_print,
            "can_edit": can_edit
        }

    @classmethod
    def build_detail_serializer(cls, request_obj, context=None):
        from apps.consultations.api.serializers.appointment_request_serializers import AppointmentRequestDetailSerializer
        return AppointmentRequestDetailSerializer(request_obj, context=context)

    @classmethod
    def build_conversion_response(cls, request_obj):
        # Resulting appointment details
        appointment = request_obj.appointments.filter(
            is_active=True,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED,
                AppointmentStatus.RESCHEDULED
            ]
        ).select_related('doctor', 'patient').first()
        
        if not appointment:
            return {
                "converted": False,
                "appointment": None
            }
        
        # Determine if Consultation or Treatment Case exists
        from apps.consultations.models.consultation import Consultation
        consultation_exists = Consultation.objects.filter(appointment=appointment, is_active=True).exists()
        treatment_case_exists = appointment.treatment_case_id is not None
        
        doc = appointment.doctor
        doctor_details = {
            "id": str(doc.id),
            "full_name": f"Dr. {doc.first_name} {doc.last_name}".strip() or doc.email,
            "email": doc.email
        } if doc else None

        pat = appointment.patient
        patient_details = {
            "id": str(pat.id),
            "patient_number": pat.patient_number,
            "child_name": f"{pat.child_first_name} {pat.child_last_name}".strip()
        } if pat else None

        open_appointment_url = f"/admin/appointments/{appointment.id}/"

        return {
            "converted": True,
            "appointment": {
                "id": str(appointment.id),
                "appointment_number": appointment.appointment_number,
                "appointment_date": appointment.appointment_date.strftime('%Y-%m-%d'),
                "start_time": appointment.start_time.strftime('%H:%M:%S'),
                "end_time": appointment.end_time.strftime('%H:%M:%S'),
                "duration_minutes": appointment.duration_minutes,
                "status": appointment.status,
                "status_display": appointment.get_status_display(),
                "doctor": doctor_details,
                "patient": patient_details,
                "consultation_exists": consultation_exists,
                "treatment_case_exists": treatment_case_exists,
                "open_appointment_url": open_appointment_url
            }
        }

    @classmethod
    def get_statistics(cls) -> dict:
        """
        Dashboard statistics.
        Calculates all required statistics in a optimized query.
        """
        today = timezone.localdate()
        start_of_week = today - datetime.timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        # Expression to calculate review processing duration in seconds
        processing_time_expr = ExpressionWrapper(
            F('reviewed_at') - F('created_at'),
            output_field=fields.DurationField()
        )

        # Base aggregation for counts
        stats = AppointmentRequest.objects.aggregate(
            total_requests=Count('id'),
            pending=Count('id', filter=Q(status=AppointmentRequestStatus.PENDING)),
            approved=Count('id', filter=Q(status=AppointmentRequestStatus.APPROVED)),
            rejected=Count('id', filter=Q(status=AppointmentRequestStatus.REJECTED)),
            linked_patient=Count('id', filter=Q(patient__isnull=False)),
            not_linked=Count('id', filter=Q(patient__isnull=True)),
            converted=Count('id', filter=Q(appointments__isnull=False)),
            not_converted=Count('id', filter=Q(appointments__isnull=True)),
            today_requests=Count('id', filter=Q(created_at__date=today)),
            this_week_requests=Count('id', filter=Q(created_at__date__gte=start_of_week)),
            this_month_requests=Count('id', filter=Q(created_at__date__gte=start_of_month)),
        )

        # Average processing time (future-ready) for reviewed requests
        avg_processing = AppointmentRequest.objects.filter(
            reviewed_at__isnull=False
        ).annotate(
            duration=processing_time_expr
        ).aggregate(
            avg_duration=Avg('duration')
        )

        avg_duration = avg_processing.get('avg_duration')
        avg_seconds = avg_duration.total_seconds() if avg_duration is not None else 0.0

        stats['avg_processing_time_seconds'] = avg_seconds
        # Readable format: e.g. "2.5 hours" or "15 minutes"
        if avg_seconds > 0:
            minutes = avg_seconds / 60
            if minutes < 60:
                stats['avg_processing_time_readable'] = f"{round(minutes, 1)} minutes"
            else:
                hours = minutes / 60
                stats['avg_processing_time_readable'] = f"{round(hours, 1)} hours"
        else:
            stats['avg_processing_time_readable'] = "N/A"

        return stats

    @classmethod
    def list_appointment_requests(cls, query_params) -> Q:
        """
        Builds and returns the filtered, annotated, and ordered queryset for AppointmentRequests.
        """
        queryset = AppointmentRequest.objects.select_related(
            'patient',
            'reviewed_by',
            'patient_linked_by',
            'patient_created_by'
        ).prefetch_related(
            'appointments',
            'appointments__doctor'
        )

        # Annotations
        queryset = queryset.annotate(
            parent_name_concat=Concat('parent_first_name', Value(' '), 'parent_last_name', output_field=CharField()),
            child_name_concat=Concat('child_first_name', Value(' '), 'child_last_name', output_field=CharField()),
            appointment_created_annotated=Exists(Appointment.objects.filter(appointment_request=OuterRef('pk'))),
            doctor_name_concat=Concat('appointments__doctor__first_name', Value(' '), 'appointments__doctor__last_name', output_field=CharField())
        )

        # 1. Search
        search = query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(request_number__icontains=search) |
                Q(parent_first_name__icontains=search) |
                Q(parent_last_name__icontains=search) |
                Q(child_first_name__icontains=search) |
                Q(child_last_name__icontains=search) |
                Q(mobile_number__icontains=search) |
                Q(email__icontains=search) |
                Q(primary_concern__icontains=search)
            )

        # 2. Filters
        status_val = query_params.get('status')
        if status_val:
            queryset = queryset.filter(status=status_val)

        doctor_id = query_params.get('doctor')
        if doctor_id:
            queryset = queryset.filter(appointments__doctor_id=doctor_id)

        appt_type = query_params.get('appointment_type')
        if appt_type:
            queryset = queryset.filter(appointment_type=appt_type)

        booking_src = query_params.get('booking_source')
        if booking_src:
            queryset = queryset.filter(booking_source=booking_src)

        pref_date = query_params.get('preferred_date')
        if pref_date:
            queryset = queryset.filter(preferred_date=pref_date)

        created_date = query_params.get('created_date')
        if created_date:
            queryset = queryset.filter(created_at__date=created_date)

        reviewed_by = query_params.get('reviewed_by')
        if reviewed_by:
            queryset = queryset.filter(reviewed_by_id=reviewed_by)

        patient_linked = query_params.get('patient_linked')
        if patient_linked is not None:
            is_linked = patient_linked.lower() == 'true'
            queryset = queryset.filter(patient__isnull=not is_linked)

        appt_converted = query_params.get('appointment_converted')
        if appt_converted is not None:
            is_converted = appt_converted.lower() == 'true'
            queryset = queryset.filter(appointment_created_annotated=is_converted)

        gender = query_params.get('gender')
        if gender:
            queryset = queryset.filter(gender=gender)

        relationship = query_params.get('relationship')
        if relationship:
            queryset = queryset.filter(relationship_to_child=relationship)

        # Date Range filters
        date_range = query_params.get('date_range')
        if date_range:
            today = timezone.localdate()
            if date_range == 'today':
                queryset = queryset.filter(created_at__date=today)
            elif date_range == 'yesterday':
                yesterday = today - datetime.timedelta(days=1)
                queryset = queryset.filter(created_at__date=yesterday)
            elif date_range == 'last_7_days':
                start_date = today - datetime.timedelta(days=7)
                queryset = queryset.filter(created_at__date__gte=start_date)
            elif date_range == 'last_30_days':
                start_date = today - datetime.timedelta(days=30)
                queryset = queryset.filter(created_at__date__gte=start_date)
            elif date_range == 'custom':
                start_date_str = query_params.get('start_date')
                end_date_str = query_params.get('end_date')
                if start_date_str and end_date_str:
                    queryset = queryset.filter(created_at__date__range=[start_date_str, end_date_str])

        # 3. Ordering
        ordering = query_params.get('ordering')
        if ordering:
            ordering_map = {
                'created_date': 'created_at',
                '-created_date': '-created_at',
                'preferred_date': 'preferred_date',
                '-preferred_date': '-preferred_date',
                'parent': 'parent_name_concat',
                '-parent': '-parent_name_concat',
                'child': 'child_name_concat',
                '-child': '-child_name_concat',
                'doctor': 'doctor_name_concat',
                '-doctor': '-doctor_name_concat',
                'status': 'status',
                '-status': '-status',
                'newest': '-created_at',
                'oldest': 'created_at'
            }
            order_fields = []
            for field in ordering.split(','):
                field = field.strip()
                if field in ordering_map:
                    order_fields.append(ordering_map[field])
            if order_fields:
                queryset = queryset.order_by(*order_fields)
            else:
                queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')

        return queryset.distinct()

    @classmethod
    @transaction.atomic
    def approve_request(cls, user, ip_address: str, request_id: str, notes: str = "") -> AppointmentRequest:
        """
        Approves an appointment request.
        """
        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Cannot approve twice or reject approved
        if request_obj.status == AppointmentRequestStatus.APPROVED:
            raise ValidationError({"non_field_errors": ["Appointment request is already approved."]})
        if request_obj.status == AppointmentRequestStatus.REJECTED:
            raise ValidationError({"non_field_errors": ["Cannot approve a rejected appointment request."]})

        old_status = request_obj.status

        # Perform status change
        request_obj.status = AppointmentRequestStatus.APPROVED
        request_obj.reviewed_by = user
        request_obj.reviewed_at = timezone.now()
        if notes:
            request_obj.additional_notes = f"{request_obj.additional_notes or ''}\nApproval Notes: {notes}".strip()
        request_obj.save()

        # Write Timeline Event
        if request_obj.patient:
            PatientTimeline.objects.create(
                patient=request_obj.patient,
                event="Appointment Approved",
                description=f"Appointment request {request_obj.request_number} was approved.",
                performed_by=user
            )

        # Write Request-Specific Timeline Event
        cls.log_timeline(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.APPROVED,
            title="Approved",
            description=f"Appointment request {request_obj.request_number} was approved.",
            performed_by=user,
            icon="thumb_up",
            color="green",
            metadata={"notes": notes}
        )

        # Write Request-Specific Activity Log
        cls.log_activity(
            appointment_request=request_obj,
            action="Status Changed",
            performed_by=user,
            old_values={"status": old_status},
            new_values={"status": AppointmentRequestStatus.APPROVED},
            ip_address=ip_address
        )

        # Audit Log
        desc = f"{user.email} approved appointment request {request_obj.request_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_REQUEST_APPROVED,
            description=desc,
            ip_address=ip_address
        )

        return request_obj

    @classmethod
    @transaction.atomic
    def reject_request(cls, user, ip_address: str, request_id: str, reason: str) -> AppointmentRequest:
        """
        Rejects an appointment request with a mandatory reason.
        """
        if not reason or not reason.strip():
            raise ValidationError({"reason": "Rejection reason is required."})

        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # Validations
        if request_obj.status == AppointmentRequestStatus.APPROVED:
            raise ValidationError({"non_field_errors": ["Cannot reject an already approved request."]})
        if request_obj.status == AppointmentRequestStatus.REJECTED:
            raise ValidationError({"non_field_errors": ["Cannot reject an already rejected request."]})
        if Appointment.objects.filter(appointment_request=request_obj, is_active=True).exists():
            raise ValidationError({"non_field_errors": ["Cannot reject a converted request."]})

        old_status = request_obj.status

        request_obj.status = AppointmentRequestStatus.REJECTED
        request_obj.rejection_reason = reason
        request_obj.reviewed_by = user
        request_obj.reviewed_at = timezone.now()
        request_obj.save()

        # Timeline Event
        if request_obj.patient:
            PatientTimeline.objects.create(
                patient=request_obj.patient,
                event="Appointment Request Rejected",
                description=f"Appointment request {request_obj.request_number} was rejected. Reason: {reason}",
                performed_by=user
            )

        # Request-Specific Timeline Event
        cls.log_timeline(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.REJECTED,
            title="Rejected",
            description=f"Appointment request {request_obj.request_number} was rejected. Reason: {reason}",
            performed_by=user,
            icon="thumb_down",
            color="red",
            metadata={"reason": reason}
        )

        # Request-Specific Activity Log
        cls.log_activity(
            appointment_request=request_obj,
            action="Status Changed",
            performed_by=user,
            old_values={"status": old_status},
            new_values={"status": AppointmentRequestStatus.REJECTED, "rejection_reason": reason},
            ip_address=ip_address
        )

        # Audit Log
        desc = f"{user.email} rejected appointment request {request_obj.request_number}. Reason: {reason}"
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_REQUEST_REJECTED,
            description=desc,
            ip_address=ip_address
        )

        return request_obj

    @classmethod
    @transaction.atomic
    def link_patient(cls, user, ip_address: str, request_id: str, patient_id: str) -> AppointmentRequest:
        """
        Links an existing patient to the appointment request.
        """
        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        patient = Patient.objects.filter(id=patient_id, is_deleted=False).first()
        if not patient:
            raise ValidationError({"patient_id": "Patient not found or has been soft-deleted."})

        if request_obj.patient:
            raise ValidationError({"non_field_errors": ["Patient is already linked to this request."]})

        old_status = request_obj.status

        # Duplicate checking warnings/errors
        # If another active patient has the same mobile
        if Patient.objects.filter(mobile_number=patient.mobile_number, is_deleted=False).exclude(id=patient.id).exists():
            # Return duplicate mobile warning
            pass
        
        # Check duplicate child: same name and DOB
        if Patient.objects.filter(
            child_first_name__iexact=patient.child_first_name,
            child_last_name__iexact=patient.child_last_name,
            date_of_birth=patient.date_of_birth,
            is_deleted=False
        ).exclude(id=patient.id).exists():
            pass

        request_obj.patient = patient
        request_obj.status = AppointmentRequestStatus.PATIENT_LINKED
        request_obj.patient_linked_by = user
        request_obj.patient_linked_at = timezone.now()
        request_obj.save()

        # Timelines
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

        # Request-Specific Timeline Event
        cls.log_timeline(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.PATIENT_LINKED,
            title="Patient Linked",
            description=f"Request {request_obj.request_number} was linked to patient {patient.patient_number}.",
            performed_by=user,
            icon="link",
            color="teal",
            metadata={"patient_id": str(patient.id), "patient_number": patient.patient_number}
        )

        # Request-Specific Activity Log
        cls.log_activity(
            appointment_request=request_obj,
            action="Relationship Added",
            performed_by=user,
            old_values={"status": old_status, "patient_id": None},
            new_values={"status": AppointmentRequestStatus.PATIENT_LINKED, "patient_id": str(patient.id), "patient_number": patient.patient_number},
            ip_address=ip_address
        )

        # Audit
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
        Creates a new patient record from the appointment request data and links it.
        """
        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        if request_obj.patient:
            raise ValidationError({"non_field_errors": ["A patient is already linked/created for this request."]})

        old_status = request_obj.status

        # Duplicate checking: prevent if exact match exists (score >= 95)
        # We search matching patients
        from apps.consultations.services.patient_matching_service import PatientMatchingService
        matches_data = PatientMatchingService.find_matches(request_id)
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
            address="", # No address in request, default to empty
            referral_source=request_obj.referral_source,
            notes=request_obj.primary_concern,
            created_by=user,
            is_deleted=False
        )
        patient.save()

        request_obj.patient = patient
        request_obj.status = AppointmentRequestStatus.PATIENT_CREATED
        request_obj.patient_created_by = user
        request_obj.patient_created_at = timezone.now()
        request_obj.save()

        # Timelines
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

        # Request-Specific Timeline Event
        cls.log_timeline(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.PATIENT_CREATED,
            title="Patient Created",
            description=f"New patient record {patient.patient_number} was created from this request.",
            performed_by=user,
            icon="person_add",
            color="purple",
            metadata={"patient_id": str(patient.id), "patient_number": patient.patient_number}
        )

        # Request-Specific Activity Log
        cls.log_activity(
            appointment_request=request_obj,
            action="Patient Created",
            performed_by=user,
            old_values={"status": old_status, "patient_id": None},
            new_values={"status": AppointmentRequestStatus.PATIENT_CREATED, "patient_id": str(patient.id), "patient_number": patient.patient_number},
            ip_address=ip_address
        )

        # Audit Log
        desc = f"{user.email} created Patient {patient.patient_number} from appointment request {request_obj.request_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.PATIENT_CREATED,
            description=desc,
            ip_address=ip_address
        )

        return patient

    @classmethod
    @transaction.atomic
    def convert_to_appointment(
        cls,
        user,
        ip_address: str,
        request_id: str,
        doctor_id: str,
        appointment_date: datetime.date,
        start_time: datetime.time,
        end_time: datetime.time
    ) -> Appointment:
        """
        Converts an approved appointment request into a confirmed appointment with full schedule verification.
        """
        request_obj = AppointmentRequest.objects.select_for_update().filter(id=request_id).first()
        if not request_obj:
            raise ValidationError({"request_id": "Appointment request not found."})

        # 1. State Validations
        if request_obj.status != AppointmentRequestStatus.APPROVED:
            raise ValidationError({"non_field_errors": [f"Cannot convert request to appointment. Request must be in APPROVED status, current status is {request_obj.status}."]})
        if not request_obj.patient:
            raise ValidationError({"non_field_errors": ["Cannot convert request. No patient is linked to this request."]})
        if Appointment.objects.filter(appointment_request=request_obj, is_active=True).exists():
            raise ValidationError({"non_field_errors": ["Appointment request has already been converted to an appointment."]})

        # 2. Patient Validation
        patient = request_obj.patient
        if patient.is_deleted:
            raise ValidationError({"patient": "Linked patient has been soft-deleted."})

        # 3. Doctor Validation
        doctor = User.objects.filter(id=doctor_id, user_roles__role__name='DOCTOR').first()
        if not doctor:
            raise ValidationError({"doctor": "Selected doctor does not exist or does not have Doctor role."})
        if not doctor.is_active:
            raise ValidationError({"doctor": "Selected doctor is inactive."})

        # 4. Clinic Settings Validation
        clinic_settings = ClinicSettings.objects.filter(is_active=True).first()
        if not clinic_settings:
            raise ValidationError({"non_field_errors": "Active clinic settings not found."})

        today = timezone.localdate()
        if appointment_date < today:
            raise ValidationError({"appointment_date": "Appointment date cannot be in the past."})
        if appointment_date > today + datetime.timedelta(days=clinic_settings.booking_window_days):
            raise ValidationError({"appointment_date": f"Appointment date is outside the booking window (max {clinic_settings.booking_window_days} days)."})
        if appointment_date == today and not clinic_settings.allow_same_day_booking:
            raise ValidationError({"appointment_date": "Same day booking is disabled in clinic settings."})

        # Weekday Enum
        weekday_map = {
            0: Weekday.MONDAY,
            1: Weekday.TUESDAY,
            2: Weekday.WEDNESDAY,
            3: Weekday.THURSDAY,
            4: Weekday.FRIDAY,
            5: Weekday.SATURDAY,
            6: Weekday.SUNDAY
        }
        weekday_enum = weekday_map[appointment_date.weekday()]

        # 5. Clinic Open Check
        weekly_sched = ClinicWeeklySchedule.objects.filter(weekday=weekday_enum).first()
        if not weekly_sched or not weekly_sched.is_open:
            raise ValidationError({"appointment_date": "Clinic is closed on this day of the week."})
        
        # Check clinic operating hours
        if start_time < weekly_sched.opening_time or end_time > weekly_sched.closing_time:
            raise ValidationError({"start_time": f"Appointment slot ({start_time} - {end_time}) falls outside clinic operating hours ({weekly_sched.opening_time} - {weekly_sched.closing_time})."})

        # 6. Clinic Holiday Check
        if ClinicHoliday.objects.filter(holiday_date=appointment_date, is_active=True).exists():
            raise ValidationError({"appointment_date": "Selected date is a clinic holiday."})

        # 7. Doctor Availability Check
        availability = DoctorAvailability.objects.filter(doctor=doctor, is_active=True).first()
        if not availability or not availability.accepts_appointments:
            raise ValidationError({"doctor": "Doctor is not currently accepting appointments."})

        # 8. Doctor Working Day Check
        working_day = DoctorWorkingDay.objects.filter(doctor=doctor, weekday=weekday_enum).first()
        if not working_day or not working_day.is_working:
            raise ValidationError({"appointment_date": "Doctor does not work on this day of the week."})
        if start_time < working_day.start_time or end_time > working_day.end_time:
            raise ValidationError({"start_time": f"Appointment slot ({start_time} - {end_time}) falls outside doctor's working hours ({working_day.start_time} - {working_day.end_time})."})

        # 9. Doctor Leave Check
        on_leave = DoctorLeave.objects.filter(
            doctor=doctor,
            is_active=True,
            start_date__lte=appointment_date,
            end_date__gte=appointment_date
        ).exists()
        if on_leave:
            raise ValidationError({"appointment_date": "Doctor is on leave on the selected date."})

        # 10. Clinic Breaks Overlap Check
        breaks = ClinicBreak.objects.filter(weekday=weekday_enum, is_active=True)
        for brk in breaks:
            if start_time < brk.end_time and end_time > brk.start_time:
                raise ValidationError({"start_time": f"Selected slot overlaps with clinic break '{brk.break_name}' ({brk.start_time} - {brk.end_time})."})

        # 11. Doctor Blocked Slot Overlap Check
        blocked_slots = DoctorBlockedSlot.objects.filter(doctor=doctor, block_date=appointment_date, is_active=True)
        for block in blocked_slots:
            if start_time < block.end_time and end_time > block.start_time:
                raise ValidationError({"start_time": f"Selected slot overlaps with doctor's blocked slot ({block.start_time} - {block.end_time})."})

        # 12. Lock appointments for concurrency check
        list(Appointment.objects.select_for_update().filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED
            ],
            is_active=True
        ))

        # 13. Existing Doctor Appointment Overlap Check
        overlapping_appts = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED
            ],
            is_active=True
        )
        for appt in overlapping_appts:
            if start_time < appt.end_time and end_time > appt.start_time:
                raise ValidationError({"start_time": f"Selected slot overlaps with another appointment ({appt.start_time} - {appt.end_time}) for this doctor."})

        # 14. Max Daily Clinic Appointments Check
        total_clinic_appts = Appointment.objects.filter(
            appointment_date=appointment_date,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED
            ],
            is_active=True
        ).count()
        if total_clinic_appts >= clinic_settings.max_daily_appointments:
            raise ValidationError({"appointment_date": f"Clinic has reached its maximum daily appointments limit ({clinic_settings.max_daily_appointments}) on this day."})

        # 15. Max Daily Doctor Patients Check
        total_doctor_appts = Appointment.objects.filter(
            doctor=doctor,
            appointment_date=appointment_date,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED
            ],
            is_active=True
        ).count()
        if total_doctor_appts >= availability.max_daily_patients:
            raise ValidationError({"doctor": f"Doctor has reached their maximum daily patients limit ({availability.max_daily_patients}) on this day."})

        # 16. Duplicate Appointment Prevention (Same patient, same doctor, same day OR overlapping slot)
        patient_overlap = Appointment.objects.filter(
            patient=patient,
            appointment_date=appointment_date,
            status__in=[
                AppointmentStatus.CONFIRMED,
                AppointmentStatus.CHECKED_IN,
                AppointmentStatus.IN_CONSULTATION,
                AppointmentStatus.COMPLETED
            ],
            is_active=True
        )
        for p_appt in patient_overlap:
            if start_time < p_appt.end_time and end_time > p_appt.start_time:
                raise ValidationError({"start_time": f"Patient already has an overlapping appointment ({p_appt.start_time} - {p_appt.end_time}) on this day."})
            if p_appt.doctor == doctor:
                raise ValidationError({"doctor": "Patient already has an appointment booked with this doctor on the same day."})

        # 17. Booking Source Determination
        booking_source = BookingSource.ADMIN_PANEL
        if user.has_role('RECEPTIONIST'):
            booking_source = BookingSource.RECEPTIONIST

        # 18. Generate Appointment Number
        unique_suffix = uuid.uuid4().hex[:6].upper()
        appointment_number = f"APT-{appointment_date.strftime('%Y%m%d')}-{unique_suffix}"

        # 19. Create the confirmed Appointment
        appointment = Appointment(
            appointment_number=appointment_number,
            patient=patient,
            doctor=doctor,
            appointment_request=request_obj,
            appointment_type=request_obj.appointment_type,
            booking_source=booking_source,
            status=AppointmentStatus.CONFIRMED,
            appointment_date=appointment_date,
            start_time=start_time,
            end_time=end_time,
            duration_minutes=int((datetime.datetime.combine(appointment_date, end_time) - datetime.datetime.combine(appointment_date, start_time)).total_seconds() / 60),
            visit_reason=request_obj.primary_concern,
            approved_by=user,
            created_by=user,
            is_active=True
        )
        appointment.full_clean()
        appointment.save()

        # 20. Update Request (stays APPROVED but linked)
        request_obj.save()

        # 21. Timelines and Audits
        # Patient Timeline
        PatientTimeline.objects.create(
            patient=patient,
            event="Appointment Booked",
            description=f"Appointment {appointment_number} with Dr. {doctor.email} was booked from request {request_obj.request_number}.",
            performed_by=user
        )

        # Appointment Timeline
        AppointmentTimeline.objects.create(
            appointment=appointment,
            event="Appointment Confirmed",
            description=f"Appointment converted and confirmed via request {request_obj.request_number}.",
            performed_by=user
        )

        # Status History
        AppointmentStatusHistory.objects.create(
            appointment=appointment,
            previous_status=None,
            new_status=AppointmentStatus.CONFIRMED,
            changed_by=user,
            reason="Appointment request converted to appointment."
        )

        # Request-Specific Timeline Event
        cls.log_timeline(
            appointment_request=request_obj,
            event_code=AppointmentRequestTimelineEvent.APPOINTMENT_CREATED,
            title="Appointment Created",
            description=f"Appointment {appointment_number} with Dr. {doctor.email} was successfully created from this request.",
            performed_by=user,
            icon="event",
            color="indigo",
            metadata={"appointment_id": str(appointment.id), "appointment_number": appointment.appointment_number, "doctor_id": str(doctor.id)}
        )

        # Request-Specific Activity Log
        cls.log_activity(
            appointment_request=request_obj,
            action="Appointment Generated",
            performed_by=user,
            old_values={"status": request_obj.status, "appointment_id": None},
            new_values={"status": request_obj.status, "appointment_id": str(appointment.id), "appointment_number": appointment.appointment_number},
            ip_address=ip_address
        )

        # Activity Log
        desc = f"{user.email} converted appointment request {request_obj.request_number} to Appointment {appointment_number}."
        ActivityLog.objects.create(
            user=user,
            action=ActivityType.APPOINTMENT_CREATED,
            description=desc,
            ip_address=ip_address
        )

        return appointment

    @classmethod
    @transaction.atomic
    def bulk_approve(cls, user, ip_address: str, ids: list) -> dict:
        """
        Performs bulk approval of requests in a transaction, supporting partial success.
        """
        approved = []
        skipped = []
        errors = {}

        if not ids:
            raise ValidationError({"ids": "Please provide a list of IDs to approve."})

        # Lock requests
        requests = AppointmentRequest.objects.select_for_update().filter(id__in=ids)
        req_dict = {str(r.id): r for r in requests}

        for req_id in ids:
            req_id_str = str(req_id)
            if req_id_str not in req_dict:
                errors[req_id_str] = "Appointment request not found."
                skipped.append(req_id_str)
                continue

            request_obj = req_dict[req_id_str]

            if request_obj.status == AppointmentRequestStatus.APPROVED:
                errors[req_id_str] = "Request is already approved."
                skipped.append(req_id_str)
                continue

            if request_obj.status == AppointmentRequestStatus.REJECTED:
                errors[req_id_str] = "Cannot approve a rejected request."
                skipped.append(req_id_str)
                continue

            # In the statistical / listing view: can_approve requires patient to be linked.
            # But wait, what if patient is not linked? Let's check:
            if not request_obj.patient:
                errors[req_id_str] = "Cannot approve request. No patient is linked."
                skipped.append(req_id_str)
                continue

            try:
                # Approve individual request
                old_status = request_obj.status
                request_obj.status = AppointmentRequestStatus.APPROVED
                request_obj.reviewed_by = user
                request_obj.reviewed_at = timezone.now()
                request_obj.save()

                PatientTimeline.objects.create(
                    patient=request_obj.patient,
                    event="Appointment Approved",
                    description=f"Appointment request {request_obj.request_number} was approved via bulk action.",
                    performed_by=user
                )

                # Request-Specific Timeline Event
                cls.log_timeline(
                    appointment_request=request_obj,
                    event_code=AppointmentRequestTimelineEvent.APPROVED,
                    title="Approved",
                    description=f"Appointment request {request_obj.request_number} was approved via bulk action.",
                    performed_by=user,
                    icon="thumb_up",
                    color="green"
                )

                # Request-Specific Activity Log
                cls.log_activity(
                    appointment_request=request_obj,
                    action="Status Changed",
                    performed_by=user,
                    old_values={"status": old_status},
                    new_values={"status": AppointmentRequestStatus.APPROVED},
                    ip_address=ip_address
                )

                desc = f"{user.email} approved appointment request {request_obj.request_number} (Bulk)."
                ActivityLog.objects.create(
                    user=user,
                    action=ActivityType.APPOINTMENT_REQUEST_APPROVED,
                    description=desc,
                    ip_address=ip_address
                )

                approved.append(req_id_str)
            except Exception as e:
                errors[req_id_str] = str(e)
                skipped.append(req_id_str)

        return {
            "approved": approved,
            "skipped": skipped,
            "errors": errors
        }

    @classmethod
    @transaction.atomic
    def bulk_reject(cls, user, ip_address: str, ids: list, reason: str) -> dict:
        """
        Performs bulk rejection of requests with a mandatory reason, supporting partial success.
        """
        rejected = []
        skipped = []
        errors = {}

        if not ids:
            raise ValidationError({"ids": "Please provide a list of IDs to reject."})
        if not reason or not reason.strip():
            raise ValidationError({"reason": "Rejection reason is required."})

        # Lock requests
        requests = AppointmentRequest.objects.select_for_update().filter(id__in=ids)
        req_dict = {str(r.id): r for r in requests}

        for req_id in ids:
            req_id_str = str(req_id)
            if req_id_str not in req_dict:
                errors[req_id_str] = "Appointment request not found."
                skipped.append(req_id_str)
                continue

            request_obj = req_dict[req_id_str]

            if request_obj.status == AppointmentRequestStatus.APPROVED:
                errors[req_id_str] = "Cannot reject an already approved request."
                skipped.append(req_id_str)
                continue

            if request_obj.status == AppointmentRequestStatus.REJECTED:
                errors[req_id_str] = "Request is already rejected."
                skipped.append(req_id_str)
                continue

            if Appointment.objects.filter(appointment_request=request_obj, is_active=True).exists():
                errors[req_id_str] = "Cannot reject a converted request."
                skipped.append(req_id_str)
                continue

            try:
                old_status = request_obj.status
                request_obj.status = AppointmentRequestStatus.REJECTED
                request_obj.rejection_reason = reason
                request_obj.reviewed_by = user
                request_obj.reviewed_at = timezone.now()
                request_obj.save()

                if request_obj.patient:
                    PatientTimeline.objects.create(
                        patient=request_obj.patient,
                        event="Appointment Request Rejected",
                        description=f"Appointment request {request_obj.request_number} was rejected via bulk action. Reason: {reason}",
                        performed_by=user
                    )

                # Request-Specific Timeline Event
                cls.log_timeline(
                    appointment_request=request_obj,
                    event_code=AppointmentRequestTimelineEvent.REJECTED,
                    title="Rejected",
                    description=f"Appointment request {request_obj.request_number} was rejected via bulk action. Reason: {reason}",
                    performed_by=user,
                    icon="thumb_down",
                    color="red",
                    metadata={"reason": reason}
                )

                # Request-Specific Activity Log
                cls.log_activity(
                    appointment_request=request_obj,
                    action="Status Changed",
                    performed_by=user,
                    old_values={"status": old_status},
                    new_values={"status": AppointmentRequestStatus.REJECTED, "rejection_reason": reason},
                    ip_address=ip_address
                )

                desc = f"{user.email} rejected appointment request {request_obj.request_number} (Bulk). Reason: {reason}"
                ActivityLog.objects.create(
                    user=user,
                    action=ActivityType.APPOINTMENT_REQUEST_REJECTED,
                    description=desc,
                    ip_address=ip_address
                )

                rejected.append(req_id_str)
            except Exception as e:
                errors[req_id_str] = str(e)
                skipped.append(req_id_str)

        return {
            "rejected": rejected,
            "skipped": skipped,
            "errors": errors
        }
