import datetime
from rest_framework import serializers
from apps.consultations.models import Patient
from apps.consultations.choices import RelationshipToChild, Gender, PatientStatus

class PatientListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer representing fields in the main patients list.
    """
    patient_id = serializers.CharField(source='patient_number', read_only=True)
    child_name = serializers.CharField(source='patient_name', read_only=True)
    parent_name = serializers.CharField(read_only=True)
    relationship = serializers.CharField(source='relationship_to_child', read_only=True)
    phone_number = serializers.CharField(source='mobile_number', read_only=True)
    status = serializers.CharField(source='patient_status', read_only=True)
    assigned_doctor = serializers.SerializerMethodField(read_only=True)
    last_visit = serializers.DateField(read_only=True)
    next_appointment = serializers.DateField(read_only=True)
    age = serializers.SerializerMethodField(read_only=True)
    photo = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_id',
            'photo',
            'child_name',
            'age',
            'gender',
            'parent_name',
            'relationship',
            'phone_number',
            'status',
            'assigned_doctor',
            'last_visit',
            'next_appointment',
            'created_at'
        ]

    def get_assigned_doctor(self, obj) -> dict:
        if obj.assigned_doctor:
            return {
                "id": obj.assigned_doctor.id,
                "name": f"Dr. {obj.assigned_doctor.first_name} {obj.assigned_doctor.last_name}",
                "email": obj.assigned_doctor.email
            }
        return None

    def get_age(self, obj) -> int:
        if not obj.date_of_birth:
            return 0
        today = datetime.date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_photo(self, obj) -> str:
        if obj.photo:
            return obj.photo.url
        return None


class PatientDetailSerializer(serializers.ModelSerializer):
    """
    Detailed profile serializer for individual Patient profiles.
    """
    patient_id = serializers.CharField(source='patient_number', read_only=True)
    age = serializers.SerializerMethodField(read_only=True)
    photo = serializers.SerializerMethodField(read_only=True)
    assigned_doctor = serializers.SerializerMethodField(read_only=True)
    created_by = serializers.SerializerMethodField(read_only=True)
    latest_appointment = serializers.SerializerMethodField(read_only=True)
    registration_date = serializers.DateTimeField(source='created_at', read_only=True)
    current_status = serializers.CharField(source='patient_status', read_only=True)

    class Meta:
        model = Patient
        fields = [
            'id',
            'patient_id',
            'photo',
            'age',
            'gender',
            'date_of_birth',
            'child_first_name',
            'child_last_name',
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'address',
            'preferred_language',
            'referral_source',
            'primary_diagnosis',
            'notes',
            'emergency_contact_name',
            'emergency_contact_phone',
            'assigned_doctor',
            'latest_appointment',
            'current_status',
            'registration_date',
            'created_by'
        ]

    def get_age(self, obj) -> int:
        if not obj.date_of_birth:
            return 0
        today = datetime.date.today()
        dob = obj.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    def get_photo(self, obj) -> str:
        if obj.photo:
            return obj.photo.url
        return None

    def get_assigned_doctor(self, obj) -> dict:
        if obj.assigned_doctor:
            return {
                "id": obj.assigned_doctor.id,
                "name": f"Dr. {obj.assigned_doctor.first_name} {obj.assigned_doctor.last_name}",
                "email": obj.assigned_doctor.email
            }
        return None

    def get_created_by(self, obj) -> dict:
        if obj.created_by:
            return {
                "id": obj.created_by.id,
                "name": f"{obj.created_by.first_name} {obj.created_by.last_name}",
                "email": obj.created_by.email
            }
        return None

    def get_latest_appointment(self, obj) -> dict:
        appt = obj.appointments.order_by('-appointment_date', '-start_time').first()
        if appt:
            return {
                "id": appt.id,
                "appointment_number": appt.appointment_number,
                "appointment_date": str(appt.appointment_date),
                "start_time": str(appt.start_time),
                "status": appt.status,
                "appointment_type": appt.appointment_type
            }
        return None


class PatientCreateSerializer(serializers.ModelSerializer):
    """
    Serializer validating payload for manual patient registration.
    """
    class Meta:
        model = Patient
        fields = [
            'child_first_name',
            'child_last_name',
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'date_of_birth',
            'gender',
            'address',
            'patient_status',
            'assigned_doctor',
            'emergency_contact_name',
            'emergency_contact_phone',
            'preferred_language',
            'referral_source',
            'primary_diagnosis',
            'notes',
            'photo'
        ]
        extra_kwargs = {
            'child_first_name': {'required': True, 'allow_blank': False},
            'child_last_name': {'required': True, 'allow_blank': False},
            'parent_first_name': {'required': True, 'allow_blank': False},
            'parent_last_name': {'required': True, 'allow_blank': False},
            'relationship_to_child': {'required': True},
            'mobile_number': {'required': True, 'allow_blank': False},
            'date_of_birth': {'required': True},
            'gender': {'required': True},
            'patient_status': {'required': True},
            'address': {'required': True, 'allow_blank': False}
        }


class PatientUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer validating payload for updating patient profiles.
    """
    class Meta:
        model = Patient
        fields = [
            'child_first_name',
            'child_last_name',
            'parent_first_name',
            'parent_last_name',
            'relationship_to_child',
            'mobile_number',
            'alternate_mobile_number',
            'email',
            'date_of_birth',
            'gender',
            'address',
            'patient_status',
            'assigned_doctor',
            'emergency_contact_name',
            'emergency_contact_phone',
            'preferred_language',
            'referral_source',
            'primary_diagnosis',
            'notes',
            'photo'
        ]


class PatientBulkActionSerializer(serializers.Serializer):
    """
    Serializer validating bulk operations on patients list.
    """
    patient_ids = serializers.ListField(
        child=serializers.UUIDField(), required=True, allow_empty=False
    )
    action = serializers.ChoiceField(
        choices=['assign_doctor', 'archive', 'activate', 'deactivate'], required=True
    )
    doctor_id = serializers.UUIDField(required=False, allow_null=True)
