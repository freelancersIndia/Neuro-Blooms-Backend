from rest_framework import serializers
from apps.consultations.models.clinic_weekly_schedule import ClinicWeeklySchedule
from apps.consultations.choices import Weekday

class WeeklyScheduleSerializer(serializers.ModelSerializer):
    weekday = serializers.ChoiceField(choices=Weekday.choices)

    class Meta:
        model = ClinicWeeklySchedule
        fields = ["weekday", "is_open", "opening_time", "closing_time"]

    def validate(self, attrs):
        is_open = attrs.get("is_open")
        opening_time = attrs.get("opening_time")
        closing_time = attrs.get("closing_time")

        if is_open:
            if not opening_time or not closing_time:
                raise serializers.ValidationError("Opening and closing times are required if the clinic is open.")
            if opening_time >= closing_time:
                raise serializers.ValidationError({"closing_time": "Closing time must be after opening time."})
        else:
            # Clear timing fields if closed
            attrs["opening_time"] = None
            attrs["closing_time"] = None

        return attrs


class WeeklyScheduleBulkUpdateSerializer(serializers.Serializer):
    schedules = WeeklyScheduleSerializer(many=True)

    def validate_schedules(self, value):
        if len(value) != 7:
            raise serializers.ValidationError("Bulk update must include exactly 7 days of the week.")

        weekdays = [item.get("weekday") for item in value]
        if len(set(weekdays)) != 7:
            raise serializers.ValidationError("Each weekday must be uniquely represented.")

        return value
