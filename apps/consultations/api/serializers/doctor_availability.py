from rest_framework import serializers
from apps.consultations.models.doctor_availability import DoctorAvailability

class DoctorAvailabilitySerializer(serializers.ModelSerializer):
    accepting_appointments = serializers.BooleanField(source="accepts_appointments")
    consultation_duration = serializers.IntegerField(source="consultation_duration_minutes")

    class Meta:
        model = DoctorAvailability
        fields = [
            "id",
            "doctor",
            "accepting_appointments",
            "consultation_duration",
            "max_daily_patients"
        ]
        read_only_fields = ["id", "doctor"]

    def validate_consultation_duration(self, value):
        allowed = [15, 20, 30, 45, 60, 90, 120]
        if value not in allowed:
            raise serializers.ValidationError(f"Consultation duration must be one of {allowed}.")
        return value

    def validate_max_daily_patients(self, value):
        if value < 1 or value > 100:
            raise serializers.ValidationError("Max daily patients must be between 1 and 100.")
        return value
