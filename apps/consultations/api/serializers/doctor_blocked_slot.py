from rest_framework import serializers
from apps.consultations.models.doctor_blocked_slot import DoctorBlockedSlot

class DoctorBlockedSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoctorBlockedSlot
        fields = [
            "id",
            "doctor",
            "block_date",
            "start_time",
            "end_time",
            "reason",
            "is_active"
        ]
        read_only_fields = ["id", "doctor", "is_active"]

    def validate_reason(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Reason cannot be blank.")
        return value
