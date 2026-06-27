import datetime
from rest_framework import serializers
from apps.consultations.models import AppointmentRequest, Patient
from apps.consultations.models.consultation import Consultation

class PatientSearchSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for manual patient search results (cards).
    """
    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_number',
            'child_first_name',
            'child_last_name',
            'parent_first_name',
            'parent_last_name',
            'mobile_number',
            'email',
            'patient_status',
            'created_at',
        ]


class PatientPreviewSerializer(serializers.ModelSerializer):
    """
    Detailed but lightweight preview serializer for a Patient.
    """
    patient_id = serializers.CharField(source='patient_number')
    photo = serializers.SerializerMethodField()
    parent = serializers.SerializerMethodField()
    child = serializers.SerializerMethodField()
    phone = serializers.CharField(source='mobile_number')
    age = serializers.SerializerMethodField()
    dob = serializers.DateField(source='date_of_birth')
    last_visit = serializers.SerializerMethodField()
    appointments_count = serializers.SerializerMethodField()
    consultations_count = serializers.SerializerMethodField()
    followups_count = serializers.SerializerMethodField()
    created_date = serializers.DateTimeField(source='created_at')

    class Meta:
        model = Patient
        fields = [
            'patient_id',
            'photo',
            'parent',
            'child',
            'phone',
            'email',
            'gender',
            'age',
            'dob',
            'last_visit',
            'appointments_count',
            'consultations_count',
            'followups_count',
            'created_date',
            'patient_status',
        ]

    def get_photo(self, obj) -> str:
        return None

    def get_parent(self, obj) -> dict:
        return {
            "first_name": obj.parent_first_name,
            "last_name": obj.parent_last_name,
            "relationship": obj.relationship_to_child
        }

    def get_child(self, obj) -> dict:
        return {
            "first_name": obj.child_first_name,
            "last_name": obj.child_last_name
        }

    def get_age(self, obj) -> int:
        if not obj.date_of_birth:
            return 0
        today = datetime.date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_last_visit(self, obj) -> str:
        last_appt = obj.appointments.filter(status='COMPLETED').order_by('-appointment_date').first()
        return str(last_appt.appointment_date) if last_appt else None

    def get_appointments_count(self, obj) -> int:
        return obj.appointments.count()

    def get_consultations_count(self, obj) -> int:
        return Consultation.objects.filter(appointment__patient=obj).count()

    def get_followups_count(self, obj) -> int:
        return obj.appointments.filter(appointment_type='FOLLOW_UP').count()


class AppointmentRequestSummarySerializer(serializers.ModelSerializer):
    """
    Summary serializer for appointment requests used on matching screen.
    """
    class Meta:
        model = AppointmentRequest
        fields = [
            'id',
            'request_number',
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'child_first_name',
            'child_last_name',
            'date_of_birth',
            'gender',
            'appointment_type',
            'primary_concern',
            'preferred_date',
            'preferred_time_slot',
            'additional_notes',
            'referral_source',
            'booking_source',
            'status',
            'created_at',
        ]


class PatientMatchingCandidateSerializer(serializers.Serializer):
    """
    Serializer representing a matching patient candidate with match metadata.
    """
    patient = PatientSearchSerializer()
    score = serializers.FloatField()
    confidence_level = serializers.CharField()


class PatientMatchingScreenSerializer(serializers.Serializer):
    """
    Primary matching screen response serializer.
    """
    appointment_request = AppointmentRequestSummarySerializer()
    best_match_score = serializers.FloatField()
    matching_patients = PatientMatchingCandidateSerializer(many=True)
    matching_statistics = serializers.JSONField()


class PatientLinkSerializer(serializers.Serializer):
    """
    Validates linking payload containing target patient's patient number.
    """
    patient_id = serializers.CharField(max_length=50, required=True)
