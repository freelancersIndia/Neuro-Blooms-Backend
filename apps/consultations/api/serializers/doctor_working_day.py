from rest_framework import serializers
from apps.consultations.models.doctor_working_day import DoctorWorkingDay
from apps.consultations.choices import Weekday

class DoctorWorkingDaySerializer(serializers.ModelSerializer):
    weekday = serializers.ChoiceField(choices=Weekday.choices)
    opening_time = serializers.TimeField(source="start_time", required=False, allow_null=True)
    closing_time = serializers.TimeField(source="end_time", required=False, allow_null=True)

    class Meta:
        model = DoctorWorkingDay
        fields = [
            "weekday",
            "is_working",
            "opening_time",
            "closing_time"
        ]

    def validate(self, attrs):
        is_working = attrs.get("is_working")
        # Extract from model source names
        start_time = attrs.get("start_time")
        end_time = attrs.get("end_time")

        if is_working:
            if not start_time or not end_time:
                raise serializers.ValidationError("Opening and closing times are required if doctor is working.")
            if start_time >= end_time:
                raise serializers.ValidationError({"closing_time": "Closing time must be after opening time."})
        else:
            # Clear timing if not working
            attrs["start_time"] = None
            attrs["end_time"] = None

        return attrs


class DoctorWorkingDayBulkUpdateSerializer(serializers.Serializer):
    working_days = DoctorWorkingDaySerializer(many=True)

    def validate_working_days(self, value):
        if len(value) != 7:
            raise serializers.ValidationError("Bulk update must include exactly 7 days of the week.")

        weekdays = [item.get("weekday") for item in value]
        if len(set(weekdays)) != 7:
            raise serializers.ValidationError("Each weekday must be uniquely represented.")

        return value
