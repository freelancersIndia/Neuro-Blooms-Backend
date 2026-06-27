import os
import zoneinfo
from rest_framework import serializers
from apps.consultations.models.clinic_settings import ClinicSettings

class ClinicSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClinicSettings
        fields = [
            "id",
            "clinic_name",
            "clinic_logo",
            "timezone",
            "opening_time",
            "closing_time",
            "slot_duration_minutes",
            "booking_window_days",
            "allow_same_day_booking",
            "max_daily_appointments",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class ClinicSettingsUpdateSerializer(serializers.ModelSerializer):
    clinic_name = serializers.CharField(max_length=255, required=False)
    timezone = serializers.CharField(max_length=100, required=False)
    opening_time = serializers.TimeField(required=False)
    closing_time = serializers.TimeField(required=False)
    slot_duration_minutes = serializers.IntegerField(required=False)
    booking_window_days = serializers.IntegerField(required=False)
    allow_same_day_booking = serializers.BooleanField(required=False)
    max_daily_appointments = serializers.IntegerField(required=False)

    class Meta:
        model = ClinicSettings
        fields = [
            "clinic_name",
            "clinic_logo",
            "timezone",
            "opening_time",
            "closing_time",
            "slot_duration_minutes",
            "booking_window_days",
            "allow_same_day_booking",
            "max_daily_appointments",
        ]

    def validate_clinic_name(self, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise serializers.ValidationError("Clinic name cannot be blank.")
        return value

    def validate_timezone(self, value):
        if value:
            value = value.strip()
            try:
                zoneinfo.ZoneInfo(value)
            except Exception:
                raise serializers.ValidationError("Must exist in IANA timezone database.")
        return value

    def validate_slot_duration_minutes(self, value):
        allowed = [15, 20, 30, 45, 60, 90, 120]
        if value not in allowed:
            raise serializers.ValidationError(f"Slot duration must be one of {allowed}.")
        return value

    def validate_booking_window_days(self, value):
        if value < 1 or value > 365:
            raise serializers.ValidationError("Booking window days must be between 1 and 365.")
        return value

    def validate_max_daily_appointments(self, value):
        if value < 1 or value > 200:
            raise serializers.ValidationError("Maximum daily appointments must be between 1 and 200.")
        return value

    def validate_clinic_logo(self, value):
        if value:
            if value.size > 2 * 1024 * 1024:
                raise serializers.ValidationError("Logo file size cannot exceed 2 MB.")
            ext = os.path.splitext(value.name)[1].lower()
            allowed = ['.png', '.jpg', '.jpeg', '.svg']
            if ext not in allowed:
                raise serializers.ValidationError("Logo format must be PNG, JPG, JPEG, or SVG.")
        return value

    def validate(self, attrs):
        opening_time = attrs.get("opening_time", self.instance.opening_time if self.instance else None)
        closing_time = attrs.get("closing_time", self.instance.closing_time if self.instance else None)

        if opening_time and closing_time and opening_time >= closing_time:
            raise serializers.ValidationError({"closing_time": "Closing time must be after opening time."})
        return attrs
