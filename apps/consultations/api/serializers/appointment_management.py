from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.consultations.models import Appointment, AppointmentTimeline, Patient
from apps.consultations.choices import AppointmentType

User = get_user_model()

class AppointmentRequestApproveSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=True)
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AppointmentRequestRejectSerializer(serializers.Serializer):
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


class AppointmentRequestRescheduleSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=True)
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AppointmentUpdateSerializer(serializers.Serializer):
    doctor_id = serializers.UUIDField(required=False)
    appointment_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    appointment_type = serializers.ChoiceField(choices=AppointmentType.choices, required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class AppointmentRescheduleSerializer(serializers.Serializer):
    appointment_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    reason = serializers.CharField(required=False, allow_blank=True, max_length=500)


class AppointmentCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=True,
        min_length=1,
        max_length=500,
        error_messages={
            "required": "Cancellation reason is required.",
            "min_length": "Cancellation reason is required.",
            "max_length": "Cancellation reason cannot exceed 500 characters."
        }
    )


class AppointmentPatientSerializer(serializers.ModelSerializer):
    child_name = serializers.SerializerMethodField()
    parent_name = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = ["id", "patient_number", "child_name", "parent_name", "mobile_number", "email"]

    def get_child_name(self, obj):
        return f"{obj.child_first_name} {obj.child_last_name}"

    def get_parent_name(self, obj):
        return f"{obj.parent_first_name} {obj.parent_last_name}"


class AppointmentDoctorSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "first_name", "last_name", "email", "name"]

    def get_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"


class AppointmentTimelineSerializer(serializers.ModelSerializer):
    performed_by_email = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentTimeline
        fields = ["event", "description", "performed_by_email", "created_at"]

    def get_performed_by_email(self, obj):
        return obj.performed_by.email if obj.performed_by else None


class AppointmentDetailSerializer(serializers.ModelSerializer):
    patient = AppointmentPatientSerializer(read_only=True)
    doctor = AppointmentDoctorSerializer(read_only=True)
    timeline = AppointmentTimelineSerializer(source="timeline_events", many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    appointment_type_display = serializers.CharField(source="get_appointment_type_display", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "appointment_number",
            "patient",
            "doctor",
            "appointment_type",
            "appointment_type_display",
            "status",
            "status_display",
            "appointment_date",
            "start_time",
            "end_time",
            "duration_minutes",
            "visit_reason",
            "timeline"
        ]
