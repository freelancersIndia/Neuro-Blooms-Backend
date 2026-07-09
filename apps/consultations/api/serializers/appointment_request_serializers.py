from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.consultations.models import AppointmentRequest, Patient, Appointment
from apps.consultations.choices import AppointmentRequestStatus, AppointmentType, BookingSource

User = get_user_model()

class AppointmentRequestListSerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()
    child = serializers.SerializerMethodField()
    doctor = serializers.SerializerMethodField()
    status_badge = serializers.CharField(source="get_status_display", read_only=True)
    patient_linked = serializers.SerializerMethodField()
    appointment_created = serializers.SerializerMethodField()
    reviewed_by = serializers.SerializerMethodField()
    action_metadata = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentRequest
        fields = [
            "id",
            "request_number",
            "parent",
            "child",
            "doctor",
            "preferred_date",
            "preferred_time_slot",
            "appointment_type",
            "booking_source",
            "status",
            "status_badge",
            "patient_linked",
            "appointment_created",
            "reviewed_by",
            "created_at",
            "action_metadata"
        ]

    def get_parent(self, obj) -> str:
        return f"{obj.parent_first_name} {obj.parent_last_name}".strip()

    def get_child(self, obj) -> str:
        return f"{obj.child_first_name} {obj.child_last_name}".strip()

    def get_doctor(self, obj) -> str:
        # Avoid N+1 queries: rely on prefetched appointments
        appts = list(obj.appointments.all())
        if appts and appts[0].doctor:
            doc = appts[0].doctor
            return f"{doc.first_name} {doc.last_name}".strip() or doc.email
        return None

    def get_patient_linked(self, obj) -> bool:
        return obj.patient_id is not None

    def get_appointment_created(self, obj) -> bool:
        if hasattr(obj, "appointment_created_annotated"):
            return obj.appointment_created_annotated
        return obj.appointments.exists()

    def get_reviewed_by(self, obj) -> str:
        if obj.reviewed_by:
            return f"{obj.reviewed_by.first_name} {obj.reviewed_by.last_name}".strip() or obj.reviewed_by.email
        return None

    def get_action_metadata(self, obj) -> dict:
        has_patient = obj.patient_id is not None
        
        # Check if converted: has an active confirmed/checked-in/completed/in-consultation appointment
        appts = list(obj.appointments.all())
        has_appt = len(appts) > 0
        status_val = obj.status

        # can_approve: Status is PENDING, PATIENT_LINKED, PATIENT_CREATED, or RESCHEDULED, and has patient, and not converted
        can_approve = (
            status_val in [
                AppointmentRequestStatus.PENDING,
                AppointmentRequestStatus.PATIENT_LINKED,
                AppointmentRequestStatus.PATIENT_CREATED,
                "RESCHEDULED"
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

        # can_download: Always allowed
        can_download = True

        return {
            "can_approve": can_approve,
            "can_reject": can_reject,
            "can_create_patient": can_create_patient,
            "can_link_patient": can_link_patient,
            "can_convert": can_convert,
            "can_download": can_download
        }


class AppointmentRequestApprovePayloadSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AppointmentRequestRejectPayloadSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True,
        min_length=1,
        max_length=500,
        error_messages={
            "required": "Rejection reason is required.",
            "min_length": "Rejection reason is required.",
            "max_length": "Rejection reason cannot exceed 500 characters."
        }
    )


class AppointmentRequestLinkPatientPayloadSerializer(serializers.Serializer):
    patient_id = serializers.UUIDField(
        required=True,
        error_messages={
            "required": "Patient ID is required.",
            "invalid": "Invalid UUID format."
        }
    )

    def validate_patient_id(self, value):
        # Check if patient exists and not soft deleted
        if not Patient.objects.all_with_deleted().filter(id=value).exists():
            raise serializers.ValidationError("Patient not found.")
        
        patient = Patient.objects.all_with_deleted().get(id=value)
        if patient.is_deleted:
            raise serializers.ValidationError("Patient not found or has been soft-deleted.")
        
        return value


class AppointmentRequestConvertPayloadSerializer(serializers.Serializer):
    doctor = serializers.UUIDField(
        required=True,
        error_messages={
            "required": "Doctor ID is required.",
            "invalid": "Invalid UUID format."
        }
    )
    appointment_date = serializers.DateField(
        required=True,
        error_messages={
            "required": "Appointment date is required."
        }
    )
    start_time = serializers.TimeField(
        required=True,
        error_messages={
            "required": "Start time is required."
        }
    )
    end_time = serializers.TimeField(
        required=True,
        error_messages={
            "required": "End time is required."
        }
    )

    def validate(self, data):
        start = data.get("start_time")
        end = data.get("end_time")
        if start and end and start >= end:
            raise serializers.ValidationError({"end_time": "End time must be after start time."})
        return data


class AppointmentRequestBulkApprovePayloadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(error_messages={"invalid": "Invalid UUID format."}),
        allow_empty=False,
        error_messages={
            "required": "List of IDs is required.",
            "allow_empty": "Empty bulk ids are not supported."
        }
    )


class AppointmentRequestBulkRejectPayloadSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.UUIDField(error_messages={"invalid": "Invalid UUID format."}),
        allow_empty=False,
        error_messages={
            "required": "List of IDs is required.",
            "allow_empty": "Empty bulk ids are not supported."
        }
    )
    reason = serializers.CharField(
        required=True,
        min_length=1,
        max_length=500,
        error_messages={
            "required": "Rejection reason is required.",
            "min_length": "Rejection reason is required."
        }
    )


class AppointmentRequestExportPayloadSerializer(serializers.Serializer):
    format = serializers.ChoiceField(
        choices=["CSV", "Excel", "PDF"],
        required=True,
        error_messages={
            "required": "Export format is required.",
            "invalid_choice": "Unsupported export format. Supported: CSV, Excel, PDF."
        }
    )
    # The payload can contain listing query parameters as filter parameters
    status = serializers.CharField(required=False, allow_blank=True)
    doctor = serializers.UUIDField(required=False)
    appointment_type = serializers.CharField(required=False, allow_blank=True)
    booking_source = serializers.CharField(required=False, allow_blank=True)
    preferred_date = serializers.DateField(required=False)
    created_date = serializers.DateField(required=False)
    reviewed_by = serializers.UUIDField(required=False)
    patient_linked = serializers.CharField(required=False, allow_blank=True)
    appointment_converted = serializers.CharField(required=False, allow_blank=True)
    gender = serializers.CharField(required=False, allow_blank=True)
    relationship = serializers.CharField(required=False, allow_blank=True)
    date_range = serializers.CharField(required=False, allow_blank=True)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)
    search = serializers.CharField(required=False, allow_blank=True)


from django.utils import timezone
from apps.consultations.models import AppointmentRequestTimeline, AppointmentRequestActivityLog

class UserSummarySerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "full_name", "email"]

    def get_full_name(self, obj) -> str:
        return f"{obj.first_name} {obj.last_name}".strip() or obj.email


class AppointmentRequestTimelineSerializer(serializers.ModelSerializer):
    performed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = AppointmentRequestTimeline
        fields = [
            "id",
            "event_code",
            "title",
            "description",
            "performed_by",
            "metadata",
            "icon",
            "color",
            "created_at"
        ]


class AppointmentRequestActivityLogSerializer(serializers.ModelSerializer):
    performed_by = UserSummarySerializer(read_only=True)

    class Meta:
        model = AppointmentRequestActivityLog
        fields = [
            "id",
            "action",
            "performed_by",
            "old_values",
            "new_values",
            "ip_address",
            "browser",
            "user_agent",
            "booking_source",
            "created_at"
        ]


class AppointmentRequestDetailSerializer(serializers.ModelSerializer):
    # Calculated Fields
    request_summary = serializers.SerializerMethodField()
    parent_information = serializers.SerializerMethodField()
    child_information = serializers.SerializerMethodField()
    appointment_preference = serializers.SerializerMethodField()
    medical_information = serializers.SerializerMethodField()
    patient = serializers.SerializerMethodField()
    appointment = serializers.SerializerMethodField()
    action_metadata = serializers.SerializerMethodField()
    timeline_count = serializers.SerializerMethodField()
    activity_count = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentRequest
        fields = [
            "id",
            "request_summary",
            "parent_information",
            "child_information",
            "appointment_preference",
            "medical_information",
            "patient",
            "appointment",
            "action_metadata",
            "timeline_count",
            "activity_count"
        ]

    def _get_age_str(self, dob) -> str:
        if not dob:
            return "N/A"
        today = timezone.localdate()
        years = today.year - dob.year
        months = today.month - dob.month
        days = today.day - dob.day
        if days < 0:
            months -= 1
            # Approximate days calculation
            days += 30
        if months < 0:
            years -= 1
            months += 12
        
        parts = []
        if years > 0:
            parts.append(f"{years} year{'s' if years > 1 else ''}")
        if months > 0:
            parts.append(f"{months} month{'s' if months > 1 else ''}")
        if years == 0 and months == 0:
            parts.append(f"{days} day{'s' if days > 1 else ''}")
        return ", ".join(parts) if parts else f"{days} days"

    def _get_request_age_str(self, created_at) -> str:
        now = timezone.now()
        diff = now - created_at
        total_seconds = int(diff.total_seconds())
        if total_seconds < 60:
            return "Just now"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} min ago"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        days = hours // 24
        return f"{days} day{'s' if days > 1 else ''} ago"

    def _get_processing_time_str(self, created_at, reviewed_at) -> str:
        if not reviewed_at:
            return "N/A"
        diff = reviewed_at - created_at
        total_seconds = int(diff.total_seconds())
        if total_seconds < 60:
            return f"{total_seconds} seconds"
        minutes = total_seconds // 60
        if minutes < 60:
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        hours = minutes // 60
        if hours < 24:
            return f"{hours} hour{'s' if hours > 1 else ''}"
        days = hours // 24
        return f"{days} day{'s' if days > 1 else ''}"

    def get_request_summary(self, obj) -> dict:
        reviewed_by_details = None
        if obj.reviewed_by:
            reviewed_by_details = UserSummarySerializer(obj.reviewed_by).data

        return {
            "request_number": obj.request_number,
            "status": obj.status,
            "status_display": obj.get_status_display(),
            "booking_source": obj.booking_source,
            "created_at": obj.created_at.strftime('%Y-%m-%dT%H:%M:%SZ') if obj.created_at else None,
            "updated_at": obj.updated_at.strftime('%Y-%m-%dT%H:%M:%SZ') if obj.updated_at else None,
            "reviewed_by": reviewed_by_details,
            "reviewed_at": obj.reviewed_at.strftime('%Y-%m-%dT%H:%M:%SZ') if obj.reviewed_at else None,
            "request_age": self._get_request_age_str(obj.created_at),
            "processing_time": self._get_processing_time_str(obj.created_at, obj.reviewed_at)
        }

    def get_parent_information(self, obj) -> dict:
        return {
            "parent_first_name": obj.parent_first_name,
            "parent_last_name": obj.parent_last_name,
            "relationship_to_child": obj.relationship_to_child,
            "mobile_number": obj.mobile_number,
            "alternate_mobile_number": obj.alternate_mobile_number,
            "email": obj.email
        }

    def get_child_information(self, obj) -> dict:
        full_name = f"{obj.child_first_name} {obj.child_last_name}".strip()
        return {
            "child_first_name": obj.child_first_name,
            "child_last_name": obj.child_last_name,
            "child_name": full_name, # support both names
            "date_of_birth": obj.date_of_birth.strftime('%Y-%m-%d') if obj.date_of_birth else None,
            "calculated_age": self._get_age_str(obj.date_of_birth),
            "gender": obj.gender
        }

    def get_appointment_preference(self, obj) -> dict:
        # Preferred Doctor calculation: if converted, get the doctor.
        # Otherwise if rescheduled to a specific doctor, we can get that doctor.
        # Let's inspect preloaded appointments.
        doc_details = None
        appts = list(obj.appointments.all())
        if appts and appts[0].doctor:
            doc_details = UserSummarySerializer(appts[0].doctor).data

        return {
            "preferred_doctor": doc_details,
            "appointment_type": obj.appointment_type,
            "appointment_type_display": obj.get_appointment_type_display(),
            "preferred_date": obj.preferred_date.strftime('%Y-%m-%d') if obj.preferred_date else None,
            "preferred_time_slot": obj.preferred_time_slot,
            "referral_source": obj.referral_source,
            "booking_source": obj.booking_source
        }

    def get_medical_information(self, obj) -> dict:
        return {
            "primary_concern": obj.primary_concern,
            "primary_concern_display": obj.get_primary_concern_display() if hasattr(obj, 'get_primary_concern_display') else obj.primary_concern,
            "additional_notes": obj.additional_notes
        }

    def get_patient(self, obj) -> dict:
        if not obj.patient:
            return None
        pat = obj.patient
        # Fetch current doctor
        doc_details = None
        if pat.assigned_doctor:
            doc_details = UserSummarySerializer(pat.assigned_doctor).data

        photo_url = None
        if pat.photo:
            request = self.context.get("request")
            if request:
                photo_url = request.build_absolute_uri(pat.photo.url)
            else:
                photo_url = pat.photo.url

        return {
            "id": str(pat.id),
            "patient_number": pat.patient_number,
            "child_name": f"{pat.child_first_name} {pat.child_last_name}".strip(),
            "photo": photo_url,
            "current_doctor": doc_details,
            "patient_status": pat.patient_status,
            "view_patient_url": f"/admin/patients/{pat.id}/"
        }

    def get_appointment(self, obj) -> dict:
        appts = list(obj.appointments.filter(is_active=True))
        if not appts:
            return None
        appt = appts[0]
        
        doc_details = None
        if appt.doctor:
            doc_details = UserSummarySerializer(appt.doctor).data

        return {
            "id": str(appt.id),
            "appointment_number": appt.appointment_number,
            "doctor": doc_details,
            "appointment_date": appt.appointment_date.strftime('%Y-%m-%d'),
            "time_slot": f"{appt.start_time.strftime('%H:%M')} - {appt.end_time.strftime('%H:%M')}",
            "status": appt.status,
            "open_appointment_url": f"/admin/appointments/{appt.id}/"
        }

    def get_action_metadata(self, obj) -> dict:
        # Use helper from Service Layer to avoid logic leakage
        from apps.consultations.services.appointment_request_service import AppointmentRequestService
        return AppointmentRequestService.build_action_metadata(obj)

    def get_timeline_count(self, obj) -> int:
        return obj.timeline_events.count()

    def get_activity_count(self, obj) -> int:
        return obj.activity_logs.count()

