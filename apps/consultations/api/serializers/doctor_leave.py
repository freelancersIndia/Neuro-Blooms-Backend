from rest_framework import serializers
from apps.consultations.models.doctor_leave import DoctorLeave

class DoctorLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorLeave
        fields = [
            "id",
            "doctor",
            "start_date",
            "end_date",
            "reason",
            "is_active"
        ]
        read_only_fields = ["id", "doctor", "is_active"]

    def validate_reason(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Reason cannot be blank.")
            if len(value) > 1000:
                raise serializers.ValidationError("Reason cannot exceed 1000 characters.")
        return value
