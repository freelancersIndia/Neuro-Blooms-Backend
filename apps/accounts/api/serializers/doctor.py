from rest_framework import serializers
from apps.accounts.models.user import User

class DoctorListSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 
            'phone_number', 'profile_image', 'specialization', 
            'qualification', 'experience', 'is_active'
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        first = obj.first_name or ""
        last = obj.last_name or ""
        return f"{first} {last}".strip()

    def get_profile_image(self, obj) -> str:
        if not obj.profile_image:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url


class DoctorDetailSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    profile_image = serializers.SerializerMethodField()
    availability = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 
            'phone_number', 'profile_image', 'specialization', 
            'qualification', 'experience', 'is_active', 'availability',
            'created_at', 'updated_at'
        ]
        read_only_fields = fields

    def get_full_name(self, obj) -> str:
        first = obj.first_name or ""
        last = obj.last_name or ""
        return f"{first} {last}".strip()

    def get_profile_image(self, obj) -> str:
        if not obj.profile_image:
            return None
        request = self.context.get('request')
        if request is not None:
            return request.build_absolute_uri(obj.profile_image.url)
        return obj.profile_image.url

    def get_availability(self, obj) -> dict:
        from apps.consultations.services.doctor_availability_service import DoctorAvailabilityService
        try:
            availability = DoctorAvailabilityService.get_availability(obj.id)
            return {
                "accepting_appointments": availability.accepts_appointments,
                "consultation_duration": availability.consultation_duration_minutes,
                "max_daily_patients": availability.max_daily_patients
            }
        except Exception:
            return None
