from rest_framework import serializers
from apps.consultations.models import Consultation, ConsultationAttachment, Patient, Appointment
from apps.consultations.services.consultation_service import calculate_age_display

class ConsultationAttachmentSerializer(serializers.ModelSerializer):
    uploaded_by_email = serializers.EmailField(source="uploaded_by.email", read_only=True)

    class Meta:
        model = ConsultationAttachment
        fields = [
            "id",
            "original_name",
            "file_size",
            "mime_type",
            "uploaded_by",
            "uploaded_by_email",
            "created_at"
        ]
        read_only_fields = ["id", "original_name", "file_size", "mime_type", "uploaded_by", "created_at"]


class ConsultationSerializer(serializers.ModelSerializer):
    doctor_email = serializers.EmailField(source="doctor.email", read_only=True)
    appointment_number = serializers.CharField(source="appointment.appointment_number", read_only=True)
    attachments = ConsultationAttachmentSerializer(many=True, read_only=True)

    class Meta:
        model = Consultation
        fields = [
            "id",
            "appointment",
            "appointment_number",
            "doctor",
            "doctor_email",
            "chief_complaint",
            "clinical_findings",
            "diagnosis",
            "treatment_notes",
            "recommendations",
            "is_completed",
            "attachments",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "doctor", "is_completed", "attachments", "created_at", "updated_at"]


class PatientProfileSummarySerializer(serializers.ModelSerializer):
    age = serializers.SerializerMethodField()
    blood_group = serializers.SerializerMethodField()
    known_allergies = serializers.SerializerMethodField()
    medical_alerts = serializers.SerializerMethodField()

    class Meta:
        model = Patient
        fields = [
            "id",
            "patient_number",
            "child_first_name",
            "child_last_name",
            "parent_first_name",
            "parent_last_name",
            "mobile_number",
            "email",
            "date_of_birth",
            "age",
            "gender",
            "blood_group",
            "known_allergies",
            "medical_alerts",
        ]

    def get_age(self, obj):
        return calculate_age_display(obj.date_of_birth)

    def get_blood_group(self, obj):
        return None

    def get_known_allergies(self, obj):
        return None

    def get_medical_alerts(self, obj):
        return None


class MedicalHistorySummarySerializer(serializers.Serializer):
    previous_diagnoses = serializers.ListField(child=serializers.CharField())
    current_active_treatment = serializers.CharField(allow_null=True)
    total_visits = serializers.IntegerField()
    last_visit = serializers.DateField(allow_null=True)


class PatientSummaryResponseSerializer(serializers.Serializer):
    patient_profile = PatientProfileSummarySerializer()
    medical_history = MedicalHistorySummarySerializer()


class ConsultationHistorySerializer(serializers.ModelSerializer):
    doctor_name = serializers.SerializerMethodField()
    date = serializers.DateField(source="appointment.appointment_date", read_only=True)
    status = serializers.CharField(source="appointment.status", read_only=True)

    class Meta:
        model = Consultation
        fields = [
            "id",
            "date",
            "doctor_name",
            "diagnosis",
            "treatment_notes",
            "recommendations",
            "status",
        ]

    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.first_name} {obj.doctor.last_name}".strip() or obj.doctor.email
