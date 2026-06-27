from rest_framework import serializers
from apps.consultations.models.clinic_break import ClinicBreak
from apps.consultations.choices import Weekday

class ClinicBreakSerializer(serializers.ModelSerializer):
    break_name = serializers.CharField(max_length=100)
    weekday = serializers.ChoiceField(choices=Weekday.choices)

    class Meta:
        model = ClinicBreak
        fields = ["id", "break_name", "weekday", "start_time", "end_time", "is_active"]
        read_only_fields = ["id", "is_active"]

    def validate_break_name(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Break name cannot be blank.")
        return value

    def validate(self, attrs):
        from apps.consultations.services.clinic_break_service import ClinicBreakService

        weekday = attrs.get("weekday", self.instance.weekday if self.instance else None)
        start_time = attrs.get("start_time", self.instance.start_time if self.instance else None)
        end_time = attrs.get("end_time", self.instance.end_time if self.instance else None)

        current_id = self.instance.id if self.instance else None

        # Delegates to the service layer for validations
        ClinicBreakService.validate_break(weekday, start_time, end_time, current_id)
        return attrs
