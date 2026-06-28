from rest_framework import serializers
from apps.consultations.models import Appointment, Patient, Consultation, TreatmentCase, ConsultationAttachment, PatientTimeline
from apps.consultations.api.serializers.consultation import PatientProfileSummarySerializer
from apps.accounts.api.serializers.user import UserDetailSerializer

class FollowupDecisionSerializer(serializers.Serializer):
    requires_followup = serializers.BooleanField(required=True)

class FollowupCreateSerializer(serializers.Serializer):
    consultation_id = serializers.UUIDField(required=True)
    doctor_id = serializers.UUIDField(required=True)
    followup_date = serializers.DateField(required=True)
    start_time = serializers.TimeField(required=True)
    reason = serializers.CharField(required=False, max_length=500, default="Review speech improvement")
    notes = serializers.CharField(required=False, max_length=2000, allow_blank=True, default="")

class FollowupAppointmentSerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    appointment_type_display = serializers.CharField(source="get_appointment_type_display", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id",
            "appointment_number",
            "appointment_type",
            "appointment_type_display",
            "status",
            "status_display",
            "appointment_date",
            "start_time",
            "end_time",
            "duration_minutes",
            "visit_reason",
            "notes",
            "doctor_id",
            "doctor_name",
        ]

    def get_doctor_name(self, obj):
        if obj.doctor:
            return f"Dr. {obj.doctor.first_name} {obj.doctor.last_name}".strip() or obj.doctor.email
        return None

class FollowupDetailSerializer(serializers.Serializer):
    appointment = FollowupAppointmentSerializer()
    patient = PatientProfileSummarySerializer()
    doctor = UserDetailSerializer()
    previous_diagnosis = serializers.CharField(read_only=True)
    previous_treatment = serializers.CharField(read_only=True)
    reason = serializers.CharField(read_only=True)
    notes = serializers.CharField(read_only=True)

class FollowupUpdateSerializer(serializers.Serializer):
    appointment_date = serializers.DateField(required=False)
    start_time = serializers.TimeField(required=False)
    reason = serializers.CharField(required=False, max_length=500)
    notes = serializers.CharField(required=False, max_length=2000, allow_blank=True)

class FollowupCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=500)

class TreatmentCaseConsultationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Consultation
        fields = [
            "id",
            "chief_complaint",
            "clinical_findings",
            "diagnosis",
            "treatment_notes",
            "recommendations",
            "is_completed",
            "created_at",
        ]

class TreatmentCaseAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsultationAttachment
        fields = [
            "id",
            "file_name",
            "file_size",
            "file_url",
            "created_at",
        ]

class TreatmentCaseTimelineSerializer(serializers.ModelSerializer):
    performed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientTimeline
        fields = [
            "id",
            "event",
            "description",
            "performed_by_name",
            "created_at",
        ]

    def get_performed_by_name(self, obj):
        if obj.performed_by:
            return obj.performed_by.email
        return "System"

class TreatmentCaseDetailSerializer(serializers.Serializer):
    patient = PatientProfileSummarySerializer()
    treatment_case_id = serializers.UUIDField()
    status = serializers.CharField()
    primary_diagnosis = serializers.CharField()
    doctor = UserDetailSerializer()
    consultations = TreatmentCaseConsultationSerializer(many=True)
    followups = FollowupAppointmentSerializer(many=True)
    uploaded_documents = TreatmentCaseAttachmentSerializer(many=True)
    timeline = TreatmentCaseTimelineSerializer(many=True)
    case_duration_days = serializers.IntegerField()
    next_appointment = FollowupAppointmentSerializer()

class TreatmentCaseCloseSerializer(serializers.Serializer):
    closing_summary = serializers.CharField(required=True, max_length=5000)
    outcome = serializers.CharField(required=True, max_length=100)

class TreatmentCaseReopenSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, max_length=2000)
